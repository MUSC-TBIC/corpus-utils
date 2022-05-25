import sys
import logging as log

import argparse

from tqdm import tqdm

import glob
import os

import re

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

    parser.add_argument( '--types-file' ,
                         dest = 'typesFile' ,
                         help = 'XML file containing the types that need to be loaded' )
    
    parser.add_argument( '--txt-root' , default = None ,
                         required = True ,
                         dest = "txt_root",
                         help = "Directory containing input corpus in text format" )
    
    parser.add_argument( '--brat-root' , default = None ,
                         required = True ,
                         dest = "brat_root",
                         help = "Directory for input corpus in brat format (.ann files)" )

    parser.add_argument( '--cas-root' , default = None ,
                         required = True ,
                         dest = "cas_root",
                         help = "Directory for output corpus in CAS XMI formatted XML" )
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
    with open( args.typesFile , 'rb' ) as fp:
        typesystem = cassis.load_typesystem( fp )
    ############
    ## ... for OMOP CDM v5.3 NOTE_NLP table properties
    ##     https://ohdsi.github.io/CommonDataModel/cdm53.html#NOTE_NLP
    NoteNlp = typesystem.create_type( name = 'edu.musc.tbic.omop_cdm.Note_Nlp_TableProperties' ,
                                      supertypeName = 'uima.tcas.Annotation' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'note_nlp_id' ,
                               description = 'A unique identifier for the NLP record.' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'note_id' ,
                               description = 'This is the NOTE_ID for the NOTE record the NLP record is associated to.' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'section_concept_id' ,
                               description = '' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'snippet' ,
                               description = '' ,
                               rangeType = 'uima.cas.String' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'offset' ,
                               description = '' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'lexical_variant' ,
                               description = '' ,
                               rangeType = 'uima.cas.String' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'note_nlp_concept_id' ,
                               description = '' ,
                               rangeType = 'uima.cas.Integer' )
    ## TODO - this really should be an int but we can't look up the appropriate
    ##        ID without a connected OMOP CDM Concept table
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'note_nlp_source_concept_id' ,
                               description = '' ,
                               rangeType = 'uima.cas.String' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'nlp_system' ,
                               description = '' ,
                               rangeType = 'uima.cas.String' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'term_exists' ,
                               description = 'Term_exists is defined as a flag that indicates if the patient actually has or had the condition. Any of the following modifiers would make Term_exists false: Negation = true; Subject = [anything other than the patient]; Conditional = true; Rule_out = true; Uncertain = very low certainty or any lower certainties. A complete lack of modifiers would make Term_exists true. For the modifiers that are there, they would have to have these values: Negation = false; Subject = patient; Conditional = false; Rule_out = false; Uncertain = true or high or moderate or even low (could argue about low).' ,
                               rangeType = 'uima.cas.Boolean' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'term_temporal' ,
                               description = '' ,
                               rangeType = 'uima.cas.String' )
    typesystem.create_feature( domainType = NoteNlp ,
                               name = 'term_modifiers' ,
                               description = '' ,
                               rangeType = 'uima.cas.String' )
    ####
    return( typesystem )


noteNlp_typeString = 'edu.musc.tbic.omop_cdm.Note_Nlp_TableProperties'

#############################################
## core functions
#############################################

def process_cas_file( cas ,
                      input_filename ):
    brat = { 'T' : {} , 'E' : {} , 'A' : {} }
    spans = {}
    ##
    FSArray = typesystem.get_type( 'uima.cas.FSArray' )
    
    noteNlpType = typesystem.get_type( noteNlp_typeString )
    
    eventConcepts = {}
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C2184149
    ## living situation
    eventConcepts[ 'LivingStatus' ] = 'C2184149'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0439044
    ## Living Alone
    eventConcepts[ 'alone' ] = 'C0439044'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0557130
    ## Lives with family
    eventConcepts[ 'with_family' ] = 'C0557130'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C3242657
    ## unrelated person
    eventConcepts[ 'with_others' ] = 'C3242657'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0237154
    ## Homelessness
    eventConcepts[ 'homeless' ] = 'C0237154'
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0242271
    ## Employment status
    eventConcepts[ 'Employment' ] = 'C0242271'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0557351
    ## Employed
    eventConcepts[ 'employed' ] = 'C0557351'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0041674
    ## Unemployment
    eventConcepts[ 'unemployed' ] = 'C0041674'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0035345
    ## Retirement
    eventConcepts[ 'retired' ] = 'C0035345'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0682148
    ## Disability status
    eventConcepts[ 'on_disability' ] = 'C0682148'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0038492
    ## student
    eventConcepts[ 'student' ] = 'C0038492'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0555052
    ## homemaker
    eventConcepts[ 'homemaker' ] = 'C0555052'
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0001948
    ## Alcohol consumption
    eventConcepts[ 'Alcohol' ] = 'C0001948'
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0281875
    ## illicit drug use (finding)
    eventConcepts[ 'Drug' ] = 'C0281875'
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C1287520
    ## Tobacco use and exposure – finding
    eventConcepts[ 'Tobacco' ] = 'C1287520'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C1971295
    ## TOBACCO NON-USER
    eventConcepts[ 'none' ] = 'C1971295'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C1698618
    ## Ex-tobacco user
    eventConcepts[ 'past' ] = 'C1698618'
    ## https://uts.nlm.nih.gov/uts/umls/concept/C3853727
    ## Tobacco user
    eventConcepts[ 'current' ] = 'C3853727'
    ##
    eventCUIs = {}
    for concept in eventConcepts:
        cui = eventConcepts[ concept ]
        eventCUIs[ cui ] = concept
    ########
    orphanModifiers = []
    eventRelations = {}
    a_count = 0
    for annot in cas.select( 'edu.musc.tbic.omop_cdm.Note_Nlp_TableProperties' ):
        xml_id = annot[ 'note_nlp_id' ]
        tag_id = 'T{}'.format( xml_id )
        begin_offset = annot[ 'offset' ]
        lexical_variant = annot[ 'lexical_variant' ]
        end_offset = int( begin_offset ) + len( lexical_variant )
        cui = annot[ 'note_nlp_source_concept_id' ]
        if( cui in [ 'C1971295' , 'C1698618' , 'C3853727' ] ):
            concept_value = eventCUIs[ cui ]
            concept_type = 'StatusTime'
        elif( cui in [ 'C0439044' , 'C0557130' ,
                       'C3242657' , 'C0237154' ] ):
            concept_value = eventCUIs[ cui ]
            concept_type = 'TypeLiving'
        elif( cui in [ 'C0557351' , 'C0041674' , 'C0035345' ,
                       'C0682148' , 'C0038492' , 'C0555052' ] ):
            concept_value = eventCUIs[ cui ]
            concept_type = 'StatusEmploy'
        elif( cui != '' ):
            concept_type = eventCUIs[ cui ]
        else:
            concept_type = None
        ########
        if( concept_type in [ 'Alcohol' , 'Drug' , 'Tobacco' ,
                              'LivingStatus' , 'Employment' ] ):
            ####
            eventRelations[ xml_id ] = {}
            span_content = note_content[ begin_offset:end_offset ].replace( '\n' , ' ' )
            brat[ 'T' ][ xml_id ] = '{} {} {}\t{}'.format( concept_type ,
                                                           begin_offset ,
                                                           end_offset ,
                                                           span_content )
            ####
            term_modifiers = annot[ 'term_modifiers' ].split( ';' )
            try:
                term_exists = annot[ 'term_exists' ]
            except:
                term_exists = None
            try:
                term_temporal = annot[ 'term_temporal' ]
            except:
                term_temporal = None
            ####
            rels = [ '{}:{}'.format( concept_type , tag_id ) ]
            for mod_pair in term_modifiers:
                mod_key , mod_value = mod_pair.split( '=' )
                if( mod_key in [ 'Status' , 'Amount' , 'Frequency' , 'Type' , 'Method' ,
                                 'Duration' , 'History' ] ):
                    if( mod_key == 'Status' and
                        concept_type in [ 'Alcohol' , 'Drug' , 'Tobacco' , 'LivingStatus' ] ):
                        eventRelations[ int( mod_value ) ] = 'StatusTime'
                    else:
                        eventRelations[ int( mod_value ) ] = mod_key
                    rels.append( '{}:T{}'.format( mod_key , mod_value ) )
                    if( mod_key == 'Status' and
                        concept_type in [ 'Alcohol' , 'Drug' , 'Tobacco' ,
                                         'LivingStatus' ] ):
                        a_count += 1
                        brat[ 'A' ][ a_count ] = '{} T{} {}'.format( 'StatusTimeVal' ,
                                                                     mod_value ,
                                                                     term_temporal )
            brat[ 'E' ][ xml_id ] = ' '.join( rels )
            ####
        elif( concept_type in [ 'StatusTime' ,
                                'StatusEmploy' ,
                                'TypeLiving' ] ):
            ####
            span_content = note_content[ begin_offset:end_offset ].replace( '\n' , ' ' )
            brat[ 'T' ][ xml_id ] = '{} {} {}\t{}'.format( concept_type ,
                                                           begin_offset ,
                                                           end_offset ,
                                                           span_content )
        else:
            orphanModifiers.append( annot )
        ## For tobacco use alone, we could set the StatusTimeVal from
        ## the anchor but for all others we need to use the event
        ## relations so we'll skip it here, too.
        ##if( concept_type in [ 'StatusTime' ] ):
        ##    a_count += 1
        ##    brat[ 'A' ][ a_count ] = '{} {} {}'.format( 'StatusTimeVal' ,
        ##                                                tag_id ,
        ##                                                term_temporal )
        #### Employment Status Values
        if( concept_type in [ 'StatusEmploy' ] ):
            a_count += 1
            brat[ 'A' ][ a_count ] = '{} T{} {}'.format( 'StatusEmployVal' ,
                                                         xml_id ,
                                                         concept_value )
        #### Living Status Values
        if( concept_type in [ 'TypeLiving' ] ):
            a_count += 1
            brat[ 'A' ][ a_count ] = '{} T{} {}'.format( 'TypeLivingVal' ,
                                                         xml_id ,
                                                         concept_value )
    ########
    for annot in orphanModifiers:
        xml_id = annot[ 'note_nlp_id' ]
        tag_id = 'T{}'.format( xml_id )
        begin_offset = annot[ 'offset' ]
        lexical_variant = annot[ 'lexical_variant' ]
        end_offset = int( begin_offset ) + len( lexical_variant )
        span_content = note_content[ begin_offset:end_offset ].replace( '\n' , ' ' )
        concept_type = eventRelations[ xml_id ]
        brat[ 'T' ][ xml_id ] = '{} {} {}\t{}'.format( concept_type ,
                                                       begin_offset ,
                                                       end_offset ,
                                                       span_content )
    #################################
    return( brat )


if __name__ == "__main__":
    ##
    args = init_args()
    ##
    typesystem = loadTypesystem( args )
    ##
    ############################
    ## Iterate over the files, covert to brat, and write the ann files to disk
    file_list = [ os.path.basename( f ) for f in glob.glob( os.path.join( args.cas_root ,
                                                                          '*.xmi' ) ) ]
    for cas_filename in tqdm( sorted( file_list ) ,
                               file = args.progressbar_file ,
                               disable = args.progressbar_disabled ):
        plain_filename = cas_filename[ 0:-4 ]
        txt_path = os.path.join( args.txt_root ,
                                 '{}.txt'.format( plain_filename ) )
        brat_path = os.path.join( args.brat_root ,
                                  '{}.ann'.format( plain_filename ) )
        with open( os.path.join( args.cas_root ,
                                 cas_filename ) , 'rb' ) as fp:
            cas = cassis.load_cas_from_xmi( fp , typesystem = typesystem )
            with open( txt_path , 'w' ) as wp:
                note_content = cas.sofa_string
                wp.write( '{}'.format( note_content ) )
            brat = process_cas_file( cas , note_content )
            with open( brat_path , 'w' ) as wp:
                for key_type in [ 'T' , 'E' , 'A' ]:
                    for key in sorted( brat[ key_type ] ):
                        wp.write( '{}{}\t{}\n'.format( key_type , key ,
                                                       brat[ key_type ][ key ] ) )