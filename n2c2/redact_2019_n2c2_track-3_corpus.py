import os
import sys

import logging as log

import glob
from tqdm import tqdm

import argparse

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
Redact brat annotation files (.ann) by removing all span strings and
write to a new directory.
""" )
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )

    parser.add_argument( '--input-dir' , required = True ,
                         dest = "inputDir",
                         help = "Input directory containg brat ann files to redact" )

    parser.add_argument( '--output-dir' , required = True ,
                         dest = "outputDir",
                         help = "Output directory for writing the ann files" )
    
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
    if( not os.path.exists( args.inputDir ) ):
        bad_args_flag = True
        log.error( 'The input directory does not exist:  {}'.format( args.inputDir ) )
    ##
    bad_args_flag = check_dir( os.path.join( args.outputDir ) ,
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
    file_list = glob.glob( os.path.join( args.inputDir , '*.ann' ) )                                         
    for full_path in tqdm( file_list ):
        filename = os.path.basename( full_path )
        out_path = os.path.join( args.outputDir , filename )
        with open( full_path , 'r' ) as in_fp:
            with open( out_path , 'w' ) as out_fp:
                for line in in_fp:
                    line = line.strip()
                    cols = line.split( '\t' )
                    if( cols[ 0 ][ 0 ] == 'T' ):
                        out_fp.write( '{}\t{}\t{}\n'.format( cols[ 0 ] , cols[ 1 ] , '[redacted]' ) )
                    else:
                        out_fp.write( '{}\n'.format( line ) )
