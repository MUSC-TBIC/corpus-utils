import sys
import logging as log

import argparse

from tqdm import tqdm

import glob
import os
## TODO - use warnings
import warnings

import re

import random

from lxml import etree as ET

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
Normalize all years found in <DATE...TYPE="DATE".../> annotations for i2b2 datasets. New values will be between 1950 and 2021.
""" )
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )

    parser.add_argument( '--progressbar-output' ,
                         dest = 'progressbar_output' ,
                         default = 'stderr' ,
                         choices = [ 'stderr' , 'stdout' , 'none' ] ,
                         help = "Pipe the progress bar to stderr, stdout, or neither" )
    
    parser.add_argument( '--input' , required = True ,
                         dest = "input_dir",
                         help = "Input directory containing i2b2 XML files" )

    parser.add_argument( '--output' ,
                        dest = "output_dir",
                        help = "Directory for writing the output files with normalized dates" )

    parser.add_argument( '--exceptions' , default = None ,
                         dest = "exceptions_file",
                         help = "Tab-delimited list of date strings with numerical components that don't match a pattern" )
    
    ##
    return parser


def get_arguments( command_line_args ):
    parser = initialize_arg_parser()
    args = parser.parse_args( command_line_args )
    ##
    return args

def init_args():
    ##
    args = get_arguments( sys.argv[ 1: ] )
    ## Configure progressbar peformance
    if( args.progressbar_output == 'none' ):
        args.progressbar_disabled = True
        args.progressbar_file = None
    else:
        args.progressbar_disabled = False
        if( args.progressbar_output == 'stderr' ):
            args.progressbar_file = sys.stderr
        elif( args.progressbar_output == 'stdout' ):
            args.progressbar_file = sys.stdout
    bad_args_flag = False
    ##
    if( not os.path.exists( args.input_dir ) ):
        bad_args_flag = True
        log.error( 'The input dir does not exist:  {}'.format( args.input_dir ) )
    ##
    if( not os.path.exists( args.output_dir ) ):
        log.warning( 'Creating output folder:  {}'.format( args.output_dir ) )
        try:
            os.makedirs( args.output_dir )
        except OSError as e:
            log.error( 'OSError caught while trying to create output folder:  {}'.format( e ) )
        except IOError as e:
            log.error( 'IOError caught while trying to create output folder:  {}'.format( e ) )
    ##
    if( bad_args_flag ):
        log.error( "I'm bailing out of this run because of errors mentioned above." )
        exit( 1 )
    ##
    return args

#############################################
## 
#############################################

if __name__ == "__main__":
    ##
    args = init_args()
    ##
    if( args.exceptions_file is not None ):
        with open( args.exceptions_file , 'w' ) as fp:
            fp.write( '{}\t{}\t{}\t{}\n'.format( 'Filename' ,
                                                 'Begin' ,
                                                 'End' ,
                                                 'Annotation' ) )
    ##########################
    ## Walk the input directory and write each file to the new output directory
    file_list = set( [os.path.basename(x) for x in glob.glob( '{}/*.xml'.format( args.input_dir ) ) ] )
    ##########################
    for this_filename in tqdm( sorted( file_list ) , total = len( file_list ) ):
        input_file = os.path.join( args.input_dir , this_filename )
        output_file = os.path.join( args.output_dir , this_filename )
        input_tree = ET.parse( input_file )
        input_root = input_tree.getroot()
        body_node = None
        tags_node = None
        for node in input_root:
            if( node.tag == 'TEXT' ):
                body_node = node
                note_text = node.text
            elif( node.tag == 'TAGS' ):
                tags_node = node
        if( note_text is None ):
            log.warn( 'Note \'{}\' lacks a body. Skipping it.'.format( this_filename ) )
            continue
        if( tags_node is None ):
            log.warn( 'Note \'{}\' doesn\'t seem to have any <TAGS>.'.format( this_filename ) )
        for tag_node in tags_node:
            if( tag_node.tag == 'DATE' ):
                if( 'TYPE' in tag_node.attrib and
                    tag_node.attrib[ 'TYPE' ] == 'DATE' ):
                    annot_begin = int( tag_node.attrib[ 'start' ] )
                    annot_end = int( tag_node.attrib[ 'end' ] )
                    tag_text = tag_node.attrib[ 'text' ]
                    new_text = None
                    if( re.fullmatch( r'(\d\d?[ -/\.]\d{2}[ -/\.])(\d{2})' , tag_text ) or
                          re.fullmatch( r'(\d{2}[ -/\.]\d\d?[ -/\.])(\d{2})' , tag_text ) or
                          re.fullmatch( r'(\d[ -/\.]\d[ -/\.])(\d{2})' , tag_text ) or
                          re.fullmatch( r'\'(\d{2})' , tag_text ) ):
                        new_year = random.choice( [ random.randrange( 50 , 99 ) , 
                                                    random.randrange( 0 , 21 ) ] )
                        new_text = '{0}{1:02d}'.format( tag_text[ :-2 ] , new_year )
                    elif( re.fullmatch( r'(\d\d?[ -/\.]\d{2}[ -/\.])(\d{4})' , tag_text ) or
                          re.fullmatch( r'(\d{2}[ -/\.]\d\d?[ -/\.])(\d{4})' , tag_text ) or
                          re.fullmatch( r'(\d[ -/\.]\d[ -/\.])(\d{4})' , tag_text ) or
                          re.fullmatch( r'(\d\d?[ -/\.])(\d{4})' , tag_text ) or
                          re.fullmatch( r'([A-Z][a-z]+[ -/\.])(\d{4})' , tag_text ) or
                          re.fullmatch( r'(\d{4})' , tag_text ) or
                          re.fullmatch( r'.*(of|[ -/\.~])(\d{4})' , tag_text ) ):
                        new_year = random.randrange( 1950 , 2021 )
                        new_text = '{}{}'.format( tag_text[ :-4 ] , new_year )
                    elif( re.fullmatch( r'(\d{4})([ -/\.]\d\d?[ -/\.]\d\d?)' , tag_text ) or
                          re.fullmatch( r'(\d{4})([ -/\.]\d\d?)' , tag_text ) or
                          re.fullmatch( r'(\d{4})([ -/\.].*)' , tag_text ) ):
                        new_year = random.randrange( 1950 , 2021 )
                        new_text = '{}{}'.format( new_year , tag_text[ 4: ] )
                    elif( re.fullmatch( r'(\d{3}0)\'s' , tag_text ) ):
                        new_year = random.randrange( 195 , 201 )
                        new_text = '{}0\'s'.format( new_year )
                    elif( re.fullmatch( r'(\d{3}0)s' , tag_text ) ):
                        new_year = random.randrange( 195 , 201 )
                        new_text = '{}0s'.format( new_year )
                    elif( re.fullmatch( r'(\d0)\'s' , tag_text ) ):
                        new_year = random.choice( [ '5' , '6' , '7' , '8' , '9' , 
                                                    '0' , '1' ] )
                        new_text = '{}0\'s'.format( new_year )
                    elif( re.fullmatch( r'\'(\d0)s' , tag_text ) ):
                        new_year = random.choice( [ '5' , '6' , '7' , '8' , '9' , 
                                                    '0' , '1' ] )
                        new_text = '\'{}0s'.format( new_year )
                    elif( re.fullmatch( r'(\d0)s' , tag_text ) ):
                        new_year = random.choice( [ '5' , '6' , '7' , '8' , '9' , 
                                                    '0' , '1' ] )
                        new_text = '{}0s'.format( new_year )
                    elif( re.fullmatch( r'.*\d.*' , tag_text ) and
                          args.exceptions_file is not None ):
                        with open( args.exceptions_file , 'a' ) as fp:
                            fp.write( '{}\t{}\t{}\t{}\n'.format( this_filename ,
                                                                 annot_begin ,
                                                                 annot_end , 
                                                                 tag_text ) )
                    if( new_text is not None ):
                        tag_node.attrib[ 'text' ] = new_text
                        if( annot_begin == 0 ):
                            prefix = ''
                        else:
                            prefix = note_text[ 0:annot_begin ]
                        if( annot_end == len( note_text ) ):
                            suffix = ''
                        else:
                            suffix = note_text[ annot_end: ]
                        note_text = '{}{}{}'.format( prefix ,
                                                     new_text ,
                                                     suffix )
        body_node.text = ET.CDATA( note_text )
        new_tree = ET.ElementTree( input_root )
        new_tree.write( output_file , 
                        xml_declaration = True , 
                        encoding = 'utf8' )
