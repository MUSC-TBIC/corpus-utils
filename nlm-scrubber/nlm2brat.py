import logging as log

import argparse
import configparser

import os
import sys
from shutil import copyfile

import glob

from tqdm import tqdm

import re

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
Stand-alone version of Jupyter notebook
""" )
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )
    ##
    parser.add_argument( '--raw-dir' ,
                         dest = 'raw_dir' ,
                         help = 'Directory to load the original, raw files from' )
    ##
    parser.add_argument( '--processed-dir' ,
                         dest = 'proc_dir' ,
                         help = 'Directory to load the NLM-Scrubber output files from' )
    ##
    parser.add_argument( '--output-dir' ,
                         dest = 'output_dir' ,
                         help = 'Directory to write the .txt and .ann files to' )
    ##
    return parser


def get_arguments( command_line_args ):
    parser = initialize_arg_parser()
    args = parser.parse_args( command_line_args )
    return args


def init_args():
    ##
    args = get_arguments( sys.argv[ 1: ] )
    ## Set up logging
    log.basicConfig()
    formatter = log.Formatter( '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s' )
    log.getLogger().handlers[0].setFormatter( formatter )
    if args.verbose:
        log.getLogger().setLevel( log.DEBUG )
        log.info( "Verbose output." )
    return args


def extract_tag_types( txt , tag_types , start_pos , pos ):
    while( txt[ pos ] != ']' ):
        pos += 1
    pos += 1
    ##log.info( '{}|{}|{}'.format( start_pos , txt[ ( start_pos + 1 ):( pos - 1 ) ] , pos ) )
    tag_types.add( txt[ ( start_pos + 1 ):( pos - 1 ) ] )
    if( txt[ pos ] in [ ' ' , '\r' , '\n' ] and
        txt[ pos + 1 ] == '[' ):
        tag_types , pos = extract_tag_types( txt , tag_types , pos + 1 , pos + 1 )
    return( tag_types , pos )


def align_files( raw_file , processed_file , ann_file ):
    with open( raw_file , 'r' ) as fp:
        raw_txt = fp.read()
    with open( processed_file , 'r' ) as fp:
        proc_txt = fp.read()
    if( os.path.exists( ann_file ) ):
        os.remove( ann_file )
    raw_pos = 0
    proc_pos = 0
    ## Adjust for newlines and trailing whitespace
    max_raw_pos = len( raw_txt.rstrip() )
    ## Find the start of the post-text metadata
    max_proc_pos = re.search( '##### DOCUMENT #############################################################' , proc_txt ).span()[ 0 ]
    max_proc_txt = proc_txt[ :max_proc_pos ]
    ## Adjust for newlines and trailing whitespace
    max_proc_pos = len( max_proc_txt.rstrip() )
    annot_list = []
    annotation_count = 0
    matches = re.finditer( r'\[[A-Z0-9]+\+?\]' , proc_txt )
    for match in matches:
        annot = dict()
        annotation_count += 1
        annot[ 'id' ] = 'T{}'.format( annotation_count )
        annot[ 'tag' ] = match.group()[ 1:-1 ]
        annot[ 'start_offset_proc' ] = match.start()
        annot[ 'end_offset_proc' ] = match.end()
        annot_list.append( annot )
    i = 0
    merge_flag = False
    while( i < len( annot_list ) ):
        annot = annot_list[ i ]
        ################################################################
        ## For the first annotation in a document, the raw and processed
        ## first annotation begins at the same point
        if( i == 0 ):
            annot[ 'start_offset_raw' ] = annot[ 'start_offset_proc' ]
        else:
            ## Otherwise, we can calculate the raw offset of the current
            ## annotation based
            prev_start_raw = annot_list[ i - 1 ][ 'start_offset_raw' ]
            prev_start_proc = annot_list[ i - 1 ][ 'start_offset_proc' ]
            prev_end_raw = annot_list[ i - 1 ][ 'end_offset_raw' ]
            prev_end_proc = annot_list[ i - 1 ][ 'end_offset_proc' ]
            ## TODO - deal with 3 in a row
            if( i > 0 and
                ## [ANNOT][ANNOT]
                ( annot[ 'start_offset_proc' ] == annot_list[ i - 1 ][ 'end_offset_proc' ] or
                  ## [ANNOT] [ANNOT]
                  ( proc_txt[ annot[ 'start_offset_proc' ] - 1 ] == ' ' and
                    annot[ 'start_offset_proc' ] - 1 == annot_list[ i - 1 ][ 'end_offset_proc' ] ) or
                  ## [ANNOT]\n\n[ANNOT]
                  ( proc_txt[ annot[ 'start_offset_proc' ] - 1 ] == '\n' and
                    annot[ 'start_offset_proc' ] - 2 == annot_list[ i - 1 ][ 'end_offset_proc' ] ) ) ):
                log.info( 'Merging this annotation with previous annotation' )
                annot[ 'start_offset_raw' ] = prev_start_raw
                merge_flag = True
            else:
                annot[ 'start_offset_raw' ] = prev_end_raw + ( annot[ 'start_offset_proc' ] - prev_end_proc )
        ################################################################
        ## Next, we need to calculate the end offset in the
        ## raw document.
        ##log.info( '{}'.format( annot ) )
        if( annot[ 'end_offset_proc' ] == max_proc_pos ):
            ## If we're at the end of the document, we don't have to
            ## do anything clever to figure out the end offset
            annot[ 'end_offset_raw' ] = max_raw_pos
        elif( i + 1 < len( annot_list ) and
              ## [ANNOT][ANNOT]
              ( annot[ 'end_offset_proc' ] == annot_list[ i + 1 ][ 'start_offset_proc' ] or
                ## [ANNOT] [ANNOT]
                ( proc_txt[ annot[ 'end_offset_proc' ] ] == ' ' and
                  annot[ 'end_offset_proc' ] + 1 == annot_list[ i + 1 ][ 'start_offset_proc' ] ) ) ):
            ## If we're immediately followed by another annotation,
            ## then merge the two annotations since we can't distinguish
            ## between them reliably.
            log.info( 'Merging this annotation with next annotation' )
            annot[ 'end_offset_raw' ] = None
        else:
            ## Otherwise, grab the span of text between the end of this
            ## annotation and the start of the next annotation (or the
            ## end of the document).  Use that to figure out how wide
            ## the original annotation was.
            if( i + 1 < len( annot_list ) ):
                next_span = proc_txt[ annot[ 'end_offset_proc' ]:annot_list[ i + 1 ][ 'start_offset_proc' ] ]
            else:
                next_span = proc_txt[ annot[ 'end_offset_proc' ]:max_proc_pos ]
            ## Newlines are introduced prior to a tag when the annotation
            ## spans multiple lines. However, sometimes, the following span
            ## is *only* whitespace, in which case, we need to preserve it.
            if( re.search( r'[^\n\r][\n\r]$' , next_span , re.MULTILINE | re.DOTALL ) ):
                log.info( 'Stripping final newline in next_span' )
                next_span = re.sub( r'[\n\r]$' , "" , next_span )
            ##
            next_span_match = re.search( re.escape( next_span ) ,
                                         raw_txt[ annot[ 'start_offset_raw' ]: ] , 
                                         re.MULTILINE )
            annot[ 'end_offset_raw' ] = annot[ 'start_offset_raw' ] + next_span_match.start()
        ##
        if( annot[ 'end_offset_raw' ] is None ):
            annot[ 'text' ] = '(see next)'
        else:
            annot[ 'text' ] = raw_txt[ annot[ 'start_offset_raw' ]:annot[ 'end_offset_raw' ] ]
        if( merge_flag ):
            merge_flag = False
            annot_list[ i - 1 ][ 'end_offset_raw' ] = annot[ 'end_offset_raw' ]
            annot_list[ i - 1 ][ 'text' ] = annot[ 'text' ]
        ## Loop back around
        i += 1
    ####################################################################
    ## Write the extracted annotations to disk.
    with open( ann_file , 'w' ) as fp:
        for annot in annot_list:
            ## Convert newlines and carriage returns into the string "\n" for printing
            pii_str = re.sub( r'[\n\r]+' , "\\\\n" , annot[ 'text' ] )
            if( False ):
                print( '{}\t{} {} {}\t{}'.format( annot[ 'id' ] ,
                                                  annot[ 'tag' ] ,
                                                  annot[ 'start_offset_raw' ] ,
                                                  annot[ 'end_offset_raw' ] ,
                                                  pii_str ) )##annot[ 'text' ] ) )
            ##
            fp.write( '{}\t{} {} {}\t{}\n'.format( annot[ 'id' ] ,
                                                   annot[ 'tag' ] ,
                                                   annot[ 'start_offset_raw' ] ,
                                                   annot[ 'end_offset_raw' ] ,
                                                   pii_str ) )##annot[ 'text' ] ) )


if __name__ == "__main__":
    ##
    args = init_args()
    file_list = set( [os.path.basename(x) for x in glob.glob( '{}/*.txt'.format( args.raw_dir ) ) ] )
    ##########################
    for this_filename in tqdm( sorted( file_list ) , total = len( file_list ) ):
        file_root = re.sub( r'.txt$' , '' , this_filename )
        raw_file = '{}/{}'.format( args.raw_dir , this_filename )
        nphi_file = '{}/{}.nphi.txt'.format( args.proc_dir , file_root )
        ann_file = '{}/{}.ann'.format( args.output_dir , file_root )
        ##
        if( not os.path.exists( nphi_file ) ):
            log.warn( 'Processed analog (.nphi.txt) to raw file ({}) missing'.format( this_filename ) )
            continue
        else:
            log.info( '{}'.format( this_filename ) )
        copyfile( raw_file ,
                  '{}/{}'.format( args.output_dir , this_filename ) )
        ## TODO - split each file into chunks with multiple newlines in between
        ##        to simplify chunking of tags near each other
        align_files( raw_file ,
                     nphi_file ,
                     ann_file )
