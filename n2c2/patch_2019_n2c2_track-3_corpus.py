import os
import sys

import re

import argparse
import glob

import logging as log

from tqdm import tqdm

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
Patch the redacted brat annotation files (.ann) by extracting the
specified span strings from the raw note and add it into a new
annotation file.
""" )
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )

    parser.add_argument( '--input-dir' , required = True ,
                         dest = "inputDir",
                         help = "Root input directory containg a train and test folder" )

    parser.add_argument( '--output-dir' , required = True ,
                        dest = "outputDir",
                        help = "Root output directory for writing the ann files" )
    
    ##
    return parser

def get_arguments( command_line_args ):
    parser = initialize_arg_parser()
    args = parser.parse_args( command_line_args )
    ##
    return args

def check_dir( dir_of_interest , bad_args_flag ):
    if( not os.path.exists( dir_of_interest ) ):
        log.warning( 'Creating output folder:  {}'.format( dir_of_interest ) )
        try:
            os.makedirs( dir_of_interest ,
                         exist_ok = True )
        except OSError as e:
            bad_args_flag = True
            log.error( 'OSError caught while trying to create output folder:  {}'.format( e ) )
        except IOError as e:
            bad_args_flag = True
            log.error( 'IOError caught while trying to create output folder:  {}'.format( e ) )
    return bad_args_flag

def init_args():
    ##
    args = get_arguments( sys.argv[ 1: ] )
    bad_args_flag = False
    ##
    for split in [ 'train' , 'test' ]:
        for form in [ 'redacted' , 'note' ]:
            input_dir = os.path.join( args.inputDir ,
                                      split ,
                                      '{}_{}'.format( split , form ) )
            if( not os.path.exists( input_dir ) ):
                bad_args_flag = True
                log.error( 'The input directory does not exist:  {}'.format( input_dir ) )
    ##
    bad_args_flag = check_dir( os.path.join( args.outputDir ,
                                             'train' ,
                                             'train_ann' ) ,
                               bad_args_flag )
    bad_args_flag = check_dir( os.path.join( args.outputDir ,
                                             'test' ,
                                             'test_ann' ) ,
                               bad_args_flag )
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
    for split in [ 'train' , 'test' ]:
        redacted_dir = os.path.join( args.inputDir ,
                                     split ,
                                     '{}_redacted'.format( split ) )
        note_dir = os.path.join( args.inputDir ,
                                 split ,
                                 '{}_note'.format( split ) )
        ann_dir = os.path.join( args.outputDir ,
                                split ,
                                '{}_ann'.format( split ) )
        file_list = glob.glob( os.path.join( note_dir ,
                                             '*.txt' ) )
        for full_path in tqdm( file_list , desc = split ):
            note_filename = os.path.basename( full_path )
            ann_filename = re.sub( '.txt$' ,
                                   '.ann' ,
                                   note_filename )
            with open( full_path , 'r' ) as fp:
                note_contents = fp.read()
            with open( os.path.join( redacted_dir ,
                                     ann_filename ) ,
                       'r' ) as in_fp:
                with open( os.path.join( ann_dir ,
                                         ann_filename ) ,
                           'w' ) as out_fp:
                    for line in in_fp:
                        line = line.strip()
                        cols = line.split( '\t' )
                        if( cols[ 0 ][ 0 ] == 'T' ):
                            middleCols = cols[ 1 ].split( ' ' )
                            annotType = middleCols[ 0 ]
                            startOffset = int( middleCols[ 1 ] )
                            endOffset = int( middleCols[ -1 ] )
                            span = note_contents[ startOffset : endOffset ]
                            out_fp.write( '{}\t{}\t{}\n'.format( cols[ 0 ] ,
                                                                 cols[ 1 ] ,
                                                                 span ) )
                        else:
                            out_fp.write( '{}\n'.format( line ) )
