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
    matches = re.finditer( r'\[[^\]]+\]' , proc_txt )
    for match in matches:
        annot = dict()
        annotation_count += 1
        annot[ 'id' ] = 'T{}'.format( annotation_count )
        annot[ 'tag' ] = match.group()[ 1:-1 ]
        annot[ 'start_offset_proc' ] = match.start()
        annot[ 'end_offset_proc' ] = match.end()
        annot_list.append( annot )
    i = 0
    while( i < len( annot_list ) ):
        annot = annot_list[ i ]
        ##
        if( i == 0 ):
            annot[ 'start_offset_raw' ] = annot[ 'start_offset_proc' ]
        else:
            prev_start_raw = annot_list[ i - 1 ][ 'start_offset_raw' ]
            prev_start_proc = annot_list[ i - 1 ][ 'start_offset_proc' ]
            prev_end_raw = annot_list[ i - 1 ][ 'end_offset_raw' ]
            prev_end_proc = annot_list[ i - 1 ][ 'end_offset_proc' ]
            if( proc_txt[ ( annot[ 'start_offset_proc' ] - 2 ):annot[ 'start_offset_proc' ] ] == '] ' ):
                annot[ 'start_offset_raw' ] = prev_start_raw
            else:
                annot[ 'start_offset_raw' ] = prev_end_raw + ( annot[ 'start_offset_proc' ] - prev_end_proc )
        ##
        ## For the first annotation in a document, the raw and processed
        ## first annotation begins at the same point
        if( annot[ 'end_offset_proc' ] == max_proc_pos ):
            annot[ 'end_offset_raw' ] = max_raw_pos
        else:
            if( i + 1 < len( annot_list ) ):
                next_span = proc_txt[ annot[ 'end_offset_proc' ]:annot_list[ i + 1 ][ 'start_offset_proc' ] ]
            else:
                next_span = proc_txt[ annot[ 'end_offset_proc' ]:max_proc_pos ]
            ## Newlines are introduced prior to a tag when the annotation
            ## spans multiple lines
            next_span = re.sub( r'[\n\r]+$' , "" , next_span )
            next_span_match = re.search( re.escape( next_span ) ,
                                         raw_txt[ annot[ 'start_offset_raw' ]: ] , 
                                         re.MULTILINE )
            ##print( 'Next Span:||{}|\n----\n'.format( next_span ) )## , next_span_match ) )
            annot[ 'end_offset_raw' ] = annot[ 'start_offset_raw' ] + next_span_match.start()
        ##print( '{}|{}|'.format( annot[ 'tag' ] , next_span ) )
        annot[ 'text' ] = raw_txt[ annot[ 'start_offset_raw' ]:annot[ 'end_offset_raw' ] ]
        ##print( '\t{}||{}||'.format( i , annot[ 'text' ] ) )
        i += 1
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

        
    # exit
    # while( raw_pos < max_raw_pos and
    #        proc_pos < max_proc_pos ):
    #     if( raw_txt[ raw_pos ] == proc_txt[ proc_pos ] ):
    #         raw_pos += 1
    #         proc_pos += 1
    #     elif( proc_txt[ proc_pos ] not in [ '[' , '\n' , '\r' ] ):
    #         log.error( 'File \'{}\' mismatch char: {} ({}) - ({}) {}'.format( os.path.basename( raw_file ) ,
    #                                                                           raw_pos ,
    #                                                                           raw_txt[ raw_pos ] ,
    #                                                                           ##raw_txt[ ( raw_pos - 5 ):( raw_pos + 5 ) ] ,
    #                                                                           proc_txt[ proc_pos ] ,
    #                                                                           ##proc_txt[ ( proc_pos - 5 ):( proc_pos + 5 ) ] ,
    #                                                                           proc_pos ) )
    #         return
    #     else:
    #         tag_types , proc_pos = extract_tag_types( txt = proc_txt , 
    #                                                   tag_types = set() , 
    #                                                   start_pos = proc_pos ,
    #                                                   pos = proc_pos )
    #         ## Skip ahead to the next non-whitespace char
    #         ## Grab the next five words or to the next tag, whichever is first
    #         word_count = 0
    #         tail_pos = proc_pos
    #         while( proc_txt[ tail_pos ] != '[' and
    #                word_count < 5 and
    #                tail_pos < max_proc_pos ):
    #             if( proc_txt[ tail_pos ] == ' ' ):
    #                 word_count += 1
    #             tail_pos += 1
    #         tail_str = proc_txt[ proc_pos:tail_pos ].rstrip()
    #         log.info( 'Tail String = |{}|'.format( tail_str ) )
    #         start_pii = raw_pos
    #         if( tail_pos > max_proc_pos ):
    #             ## Just copy over the rest of the raw txt
    #             pii_str = raw_txt[ raw_pos:max_raw_pos ]
    #             end_pii = max_raw_pos
    #         else:
    #             ## Find the appropriate span to copy
    #             tail_length = len( tail_str )
    #             while( raw_txt[ raw_pos:( raw_pos + tail_length ) ] != tail_str ):
    #                 #log.info( '|{}|{}'.format( raw_txt[ start_pii:raw_pos ] , 
    #                 #                           raw_txt[ raw_pos:( raw_pos + tail_length ) ] ) )
    #                 raw_pos += 1
    #                 if( ( os.path.basename( raw_file ) == '101-01.txt' and
    #                       start_pii == 2236 and
    #                       raw_pos == 2251 ) ):
    #                     break
    #             end_pii = raw_pos
    #             pii_str = raw_txt[ start_pii:end_pii ]
    #         log.info( 'PII String = |{}|'.format( pii_str ) )
    #         ##
    #         annotation_count += 1
    #         with open( ann_file , 'a' ) as fp:
    #             ## Convert newlines and carriage returns into the string "\n" for printing
    #             pii_str = re.sub( r'[\n\r]+' , "\\\\n" , pii_str )
    #             for tag_type in tag_types:
    #                 fp.write( 'T{}\t{} {} {}\t{}\n'.format( annotation_count ,
    #                                                         tag_type ,
    #                                                         start_pii ,
    #                                                         end_pii ,
    #                                                         pii_str ) )
    #         raw_pos += 1
    #         proc_pos += 1
    #         log.info( 'raw_pos = {}, proc_pos = {}'.format( raw_pos , proc_pos ) )
            

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
