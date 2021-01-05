import sys
import logging as log

import argparse

from tqdm import tqdm

import glob
import os

try:
    from lxml import etree
    log.debug("running with lxml.etree")
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
        log.debug("running with cElementTree on Python 2.5+")
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
            log.debug("running with ElementTree on Python 2.5+")
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
                log.debug("running with cElementTree")
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                    log.debug("running with ElementTree")
                except ImportError:
                    log.warn("Failed to import ElementTree from any known place")

import cassis

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

    parser.add_argument( '--mapping-file' , default = None ,
                         dest = 'mapping_file' ,
                         help = "Tab-delimited files containing concepts mappings for the source ontology to the target ontology" )

    parser.add_argument( '--txt-root' , default = None ,
                         required = True ,
                         dest = "txt_root",
                         help = "Directory containing input corpus in text format" )
    parser.add_argument( '--knowtator-root' , default = None ,
                         required = True ,
                         dest = "xml_root",
                         help = "Directory containing input corpus in Knowtator format" )
    
    parser.add_argument( '--cas-root' , default = None ,
                         required = True ,
                         dest = "cas_root",
                         help = "Directory for output corpus in CAS XMI formatted XML" )
    parser.add_argument( '--brat-root' , default = None ,
                         required = True ,
                         dest = "brat_root",
                         help = "Directory for output corpus in brat format (.txt and .ann files)" )
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
    if( args.verbose ):
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
    ##
    return args


## TODO - make this easily configurable from the command line
def loadTypesystem( args ):
    ############################
    ## Create a type system
    ## - https://github.com/dkpro/dkpro-cassis/blob/master/cassis/typesystem.py
    ############
    ## ... for tokens
    typesystem = cassis.TypeSystem()
    TokenAnnotation = typesystem.create_type( name = 'uima.tt.TokenAnnotation' , 
                                              supertypeName = 'uima.tcas.Annotation' )
    typesystem.add_feature( type_ = TokenAnnotation ,
                            name = 'text' , 
                            rangeTypeName = 'uima.cas.String' )
    ############
    ## ... for sections (and, by association, section headers)
    defaultType = typesystem.create_type( name = 'edu.musc.tbic.uima.NoteSection' ,
                                          supertypeName = 'uima.tcas.Annotation' )
    typesystem.add_feature( type_ = defaultType ,
                            name = 'SectionNumber' ,
                            description = '' ,
                            rangeTypeName = 'uima.cas.Integer' )
    typesystem.add_feature( type_ = defaultType ,
                            name = 'SectionDepth' ,
                            description = 'Given an hierarchical section schema, how deep is the current section ( 0 = root level/major category)' , 
                            rangeTypeName = 'uima.cas.Integer' )
    typesystem.add_feature( type_ = defaultType ,
                            name = 'SectionId' ,
                            description = 'Type (or concept id) of current section' , 
                            rangeTypeName = 'uima.cas.String' )
    typesystem.add_feature( type_ = defaultType ,
                            name = 'beginHeader' ,
                            description = 'The start offset for this section\'s header (-1 if no header)' , 
                            rangeTypeName = 'uima.cas.Integer' )
    typesystem.add_feature( type_ = defaultType ,
                            name = 'endHeader' ,
                            description = 'The end offset for this section\'s header (-1 if no header)' , 
                            rangeTypeName = 'uima.cas.Integer' )
    typesystem.add_feature( type_ = defaultType ,
                            name = 'modifiers' ,
                            description = 'Modifiers (key/value pairs) associated with the given section' , 
                            rangeTypeName = 'uima.cas.String' )
    return( typesystem , defaultType )


#############################################
## core functions
#############################################

def loadOntologyMapping( args ):
    if( args.mapping_file is None ):
        return( {} , 'DefaultType' , None )
    ####
    ontology_mapping = {}
    with open( args.mapping_file , 'r' ) as fp:
        headers = fp.readline().strip()
        src_header , _ , tgt_header = headers.split( '\t' )
        for line in fp:
            line = line.strip()
            if( line == '' ):
                continue
            src_type , src_abbrev , tgt_type = line.split( '\t' )
            if( src_type not in ontology_mapping ):
                ontology_mapping[ src_type ] = set()
            ontology_mapping[ src_type ].add( tgt_type )
            if( src_abbrev not in ontology_mapping ):
                ontology_mapping[ src_abbrev ] = set()
            ontology_mapping[ src_abbrev ].add( tgt_type )
    ##
    return( ontology_mapping , src_header , tgt_header )


if __name__ == "__main__":
    ##
    args = init_args()
    ##
    typesystem , defaultType = loadTypesystem( args )
    ##
    ontology_mapping , src_type , tgt_type = loadOntologyMapping( args )
    ##
    ############################
    ## Iterate over the files, covert to CAS, and write the XMI to disk
    file_list = glob.glob( os.path.join( args.xml_root , '*.knowtator.xml' ) )
    for full_path in tqdm( sorted( file_list ) ,
                           file = args.progressbar_file ,
                           disable = args.progressbar_disabled ):
        xml_filename = os.path.basename( full_path )
        plain_filename = xml_filename[ 0:-14 ]
        txt_path = os.path.join( args.txt_root ,
                                 plain_filename )
        if( not os.path.exists( txt_path ) ):
            txt_path = os.path.join( args.txt_root ,
                                     '{}.txt'.format( plain_filename ) )
            if( not os.path.exists( txt_path ) ):
                log.warn( 'No matching txt file found for \'{}\''.format( xml_filename ) )
                continue
        with open( txt_path , 'r' ) as fp:
            note_contents = fp.read().strip()
        with open( full_path , 'r' ) as fp:
            tree = etree.parse( fp )
        root = tree.getroot()
        spans = {}
        for node in root:
            if( node.tag == 'annotation' ):
                mention_id = None
                begin_offset = None
                end_offset = None
                for child in node.iter():
                    if( child.tag == 'mention' ):
                        mention_id = child.attrib[ 'id' ]
                    elif( child.tag == 'span' ):
                        begin_offset = int( child.attrib[ 'start' ] )
                        end_offset = int( child.attrib[ 'end' ] )
                    elif( child.tag == 'spannedText' ):
                        text_span = child.text
                if( mention_id not in spans ):
                    spans[ mention_id ] = {}
                spans[ mention_id ][ 'begin' ] = begin_offset
                spans[ mention_id ][ 'end' ] = end_offset
                spans[ mention_id ][ 'text_span' ] = text_span
            elif( node.tag == 'classMention' ):
                mention_id = node.attrib[ 'id' ]
                mention_class = None
                for child in node.iter():
                    if( child.tag == 'mentionClass' ):
                        mention_class = child.attrib[ 'id' ]
                if( mention_id not in spans ):
                    spans[ mention_id ] = {}
                spans[ mention_id ][ 'class' ] = mention_class
        ##
        cas = cassis.Cas( typesystem = typesystem )
        cas.sofa_string = note_contents
        cas.sofa_mime = "text/plain"
        cas_path = os.path.join( args.cas_root ,
                                 '{}.xml'.format( plain_filename ) )
        brat_txt_path = os.path.join( args.brat_root ,
                                      '{}.xml'.format( plain_filename ) )
        brat_ann_path = os.path.join( args.brat_root ,
                                      '{}.ann'.format( plain_filename ) )
        with open( brat_txt_path , 'w' ) as fp:
            fp.write( '{}'.format( note_contents ) )
        with open( brat_ann_path , 'w' ) as fp:
            1 ## Clear out the old
        annot_count = 0
        normalization_count = 0
        for mention_id in spans:
            if( tgt_type is None ):
                cas.add_annotation( defaultType( beginHeader = spans[ mention_id ][ 'begin' ] ,
                                                 endHeader = spans[ mention_id ][ 'end' ] ,
                                                 SectionId = spans[ mention_id ][ 'class' ] ,
                                                 begin = '-1' ,
                                                 end = '-1' ) )
            else:
                if( spans[ mention_id ][ 'class' ] in ontology_mapping ):
                    ## We sort the entries here so output is consistent across multiple runs
                    ## if the underlying mapping file is equivalent
                    mapped_section = ','.join( sorted( ontology_mapping[ spans[ mention_id ][ 'class' ] ] ) )
                else:
                    mapped_section = 'Unknown/Unclassified'
                cas.add_annotation( defaultType( beginHeader = spans[ mention_id ][ 'begin' ] ,
                                                 endHeader = spans[ mention_id ][ 'end' ] ,
                                                 SectionId = mapped_section ,
                                                 modifiers = '{}={}'.format( src_type ,
                                                                             spans[ mention_id ][ 'class' ] ) ,
                                                 begin = '-1' ,
                                                 end = '-1' ) )
            ####
            annot_count += 1
            with open( brat_ann_path , 'a' ) as fp:
                fp.write( 'T{}\t{} {} {}\t{}\n'.format( annot_count ,
                                                        'SectionHeader' ,
                                                        spans[ mention_id ][ 'begin' ] ,
                                                        spans[ mention_id ][ 'end' ] ,
                                                        spans[ mention_id ][ 'text_span' ] ) )
                normalization_count += 1
                fp.write( 'N{}\tReference T{} {}\t{}\n'.format( normalization_count ,
                                                                annot_count ,
                                                                src_type ,
                                                                spans[ mention_id ][ 'class' ] ) )
                if( tgt_type is not None ):
                    normalization_count += 1
                    fp.write( 'N{}\tReference T{} {}\t{}\n'.format( normalization_count ,
                                                                    annot_count ,
                                                                    tgt_type ,
                                                                    mapped_section ) )
        cas.to_xmi( path = cas_path ,
                    pretty_print = True )

            
