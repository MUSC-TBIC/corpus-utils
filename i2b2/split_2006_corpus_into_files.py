from __future__ import print_function

import sys
import logging as log

from tqdm import tqdm

import glob
import os
## TODO - use warnings
import warnings

import re
import json

import argparse

import xml.etree.ElementTree as ET

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
Split a single i2b2 2006 input file into individual note files.
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
                         default = 'smokers_surrogate_train_all_version2.xml' ,
                         dest = "input_file",
                         help = "Original single XML file" )

    parser.add_argument( '--output' , default = '/tmp/i2b2_split' ,
                        dest = "output",
                        help = "Directory for writing the individual output files" )
    
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
    if( not os.path.exists( args.input_file ) ):
        bad_args_flag = True
        log.error( 'The input file does not exist:  {}'.format( args.input_file ) )
    ##
    if( not os.path.exists( args.output ) ):
        log.warning( 'Creating output folder:  {}'.format( args.output ) )
        try:
            os.makedirs( args.output )
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
    ##########################
    ## Walk the input file and collect matching annotations
    input_tree = ET.parse( args.input_file )
    input_root = input_tree.getroot()
    ## Loop over the RECORD level
    for node in input_root:
        record_id = node.attrib[ 'ID' ]
        new_tree = ET.ElementTree( node )
        output_file = '{}/{:03d}.xml'.format( args.output , int( record_id ) )
        new_tree.write( output_file , encoding='utf8')
