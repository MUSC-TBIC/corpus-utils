from __future__ import print_function

import sys
import logging as log

import argparse

from tqdm import tqdm

import glob
import os

import re

import statistics

#############################################
## helper functions
#############################################

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
""")
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )

    parser.add_argument( '--progressbar-output' ,
                         dest = 'progressbar_output' ,
                         default = 'stderr' ,
                         choices = [ 'stderr' , 'stdout' , 'none' ] ,
                         help = "Pipe the progress bar to stderr, stdout, or neither" )

    parser.add_argument( '--pretty-print' ,
                         dest = 'pretty_print' ,
                         help = "Round floats and remove decimals from integers" ,
                         action = "store_true" )

    parser.add_argument( '--input' , default = None ,
                         dest = "input",
                         help = "Directory containing input corpus" )
    parser.add_argument( '--output' , default = None ,
                        dest = "output",
                        help = "Directory for output corpus" )

    parser.add_argument("--file-prefix", 
                        dest = 'file_prefix' ,
                        default = '/' ,
                        help="Prefix used for filename matching" )
    ## TODO - lstrip hack added to handle suffixes with dashes
    ##   https://stackoverflow.com/questions/16174992/cant-get-argparse-to-read-quoted-string-with-dashes-in-it
    parser.add_argument("--file-suffix", nargs = '+' ,
                        dest = 'file_suffix' ,
                        default = [ '.txt' ] ,
                        help="Suffix used for filename matching.  You can provide a second argument if the test file suffixes don't match the reference file suffixes. The span of the reference filename that matches the file suffix will be replaced with the contents of the second suffix string.  This replacement is useful when the reference and test differ in terms of file endings (e.g., '001.txt' -> '001.xmi')" )

    parser.add_argument( '--print-metrics' , default = False ,
                         dest = 'print_metrics' ,
                         help = "Print to stdout the metrics" ,
                         action = "store_true" )

    parser.add_argument("--max-width", 
                        dest = 'max_width' ,
                        default = 80 ,
                        help = "" )

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
    ## Set up logging
    if args.verbose:
        log.basicConfig( format = "%(levelname)s: %(message)s" ,
                         level = log.DEBUG )
        log.info( "Verbose output." )
        log.debug( "{}".format( args ) )
    else:
        log.basicConfig( format="%(levelname)s: %(message)s" )
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
    ## lstrip hack added to handle prefixes and suffixes with dashes
    ##   https://stackoverflow.com/questions/16174992/cant-get-argparse-to-read-quoted-string-with-dashes-in-it
    args.file_prefix = args.file_prefix.lstrip()
    args.file_suffix[ 0 ] = args.file_suffix[ 0 ].lstrip()
    if( len( args.file_suffix ) == 2 ):
        args.file_suffix[ 1 ] = args.file_suffix[ 1 ].lstrip()
    ## Make sure the width is treated as a number
    args.max_width = int( args.max_width )
    return args

#############################################
## core functions
#############################################

def get_file_metrics( args ):
    log.debug( "Entering '{}'".format( sys._getframe().f_code.co_name ) )
    ##
    file_list = set([os.path.basename(x) for x in glob.glob( args.input +
                                                             args.file_prefix +
                                                             '*' +
                                                             args.file_suffix[ 0 ] )])
    lengths = []
    ##########################
    for this_filename in tqdm( sorted( file_list ) ,
                               file = args.progressbar_file ,
                               disable = args.progressbar_disabled ):
        try:
            this_full_path = '{}/{}'.format( args.input ,
                                             this_filename )
        except NameError as e:
            log.error( 'NameError exception in get_file_metrics:  {}'.format( e ) )
        except AttributeError as e:
            log.error( 'AttributeError exception in get_file_metrics:  {}'.format( e ) )
        except TypeError as e:
            log.error( 'TypeError exception in get_file_metrics:  {}'.format( e ) )
        except:
            e = sys.exc_info()[0]
            log.error( 'Uncaught exception in get_file_metrics:  {}'.format( e ) )
        ##
        with open( this_full_path , 'r' ) as fp:
            for line in fp:
                line = line.strip()
                if( len( line ) > 0 ):
                    lengths.append( len( line ) )
    print( 'Files:\t{}\nLines:\t{}\nMin:\t{}\nMean:\t{}\nMedian:\t{}\nMax:\t{}\n'.format(
        len( file_list ) ,
        len( lengths ) ,
        min( lengths ) ,
        statistics.mean( lengths ) ,
        statistics.median( lengths ) ,
        max( lengths ) ) )
    #########
    log.debug( "-- Leaving '{}'".format( sys._getframe().f_code.co_name ) )

def create_fixed_width( args ):
    log.debug( "Entering '{}'".format( sys._getframe().f_code.co_name ) )
    ##
    file_list = set([os.path.basename(x) for x in glob.glob( args.input +
                                                             args.file_prefix +
                                                             '*' +
                                                             args.file_suffix[ 0 ] )])
    ##########################
    for this_filename in tqdm( sorted( file_list ) ,
                               file = args.progressbar_file ,
                               disable = args.progressbar_disabled ):
        try:
            this_full_path = '{}/{}'.format( args.input ,
                                             this_filename )
            if( len( args.file_suffix ) == 1 ):
                that_filename = this_filename
            else:
                that_filename = re.sub( args.file_suffix[ 0 ] + '$' ,
                                        args.file_suffix[ 1 ] ,
                                        this_filename )
            that_full_path = '{}/{}'.format( args.output ,
                                             that_filename )
        except NameError as e:
            log.error( 'NameError exception in get_file_metrics:  {}'.format( e ) )
        except AttributeError as e:
            log.error( 'AttributeError exception in get_file_metrics:  {}'.format( e ) )
        except TypeError as e:
            log.error( 'TypeError exception in get_file_metrics:  {}'.format( e ) )
        except:
            e = sys.exc_info()[0]
            log.error( 'Uncaught exception in get_file_metrics:  {}'.format( e ) )
        ##
        with open( this_full_path , 'r' ) as in_file:
            with open( that_full_path , 'w' ) as out_file:
                for line in in_file:
                    line = line.strip()
                    if( args.max_width == -1 ):
                        out_file.write( '{} '.format( line ) )
                        continue
                    chars = list( line )
                    left_char = 0
                    right_char = min( len( line ) , args.max_width )
                    while( right_char < len( line ) ):
                        while( right_char > left_char and
                               re.match( r'\S' , chars[ right_char ] ) ):
                            right_char -= 1
                        out_file.write( '{}\n'.format( ''.join( chars[ left_char:right_char ] ) ) )
                        left_char = right_char + 1
                        right_char = min( len( line ) , right_char + args.max_width )
                    out_file.write( '{}\n'.format( ''.join( chars[ left_char:right_char ] ) ) )
                if( args.max_width == -1 ):
                    out_file.write( '\n' )
    #########
    log.debug( "-- Leaving '{}'".format( sys._getframe().f_code.co_name ) )

if __name__ == "__main__":
    ##
    args = init_args()
    ##
    if( args.print_metrics ):
        get_file_metrics( args )
    else:
        create_fixed_width( args )
