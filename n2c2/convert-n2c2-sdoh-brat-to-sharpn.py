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
    return( typesystem )


eventMention_typeString = 'org.apache.ctakes.typesystem.type.textsem.EventMention'
modifier_typeString = 'org.apache.ctakes.typesystem.type.textsem.Modifier'
timeMention_typeString = 'org.apache.ctakes.typesystem.type.textsem.TimeMention'

event_typeString = 'org.apache.ctakes.typesystem.type.refsem.Event'
eventProperties_typeString = 'org.apache.ctakes.typesystem.type.refsem.EventProperties'
attribute_typeString = 'org.apache.ctakes.typesystem.type.refsem.Attribute'

umlsConcept_typeString = 'org.apache.ctakes.typesystem.type.refsem.UmlsConcept'

relationArgument_typeString = 'org.apache.ctakes.typesystem.type.relation.RelationArgument'
binaryTextRelation_typeString = 'org.apache.ctakes.typesystem.type.relation.BinaryTextRelation'

#############################################
## core functions
#############################################

def process_ann_file( cas ,
                      input_filename ):
    spans = {}
    ##
    FSArray = typesystem.get_type( 'uima.cas.FSArray' )
    
    eventMentionType = typesystem.get_type( eventMention_typeString )
    modifierType = typesystem.get_type( modifier_typeString )
    timeMentionType = typesystem.get_type( timeMention_typeString )
    
    eventType = typesystem.get_type( event_typeString )
    eventPropertiesType = typesystem.get_type( eventProperties_typeString )
    attributeType = typesystem.get_type( attribute_typeString )
    
    umlsConceptType = typesystem.get_type( umlsConcept_typeString )
    
    relationArgumentType = typesystem.get_type( relationArgument_typeString )
    binaryTextRelationType = typesystem.get_type( binaryTextRelation_typeString )
    
    umlsConceptType = typesystem.get_type( umlsConcept_typeString )

    eventTypes = {}
    ##########################################################
    ## All Semantics Types are Finding (T033) unless otherwise
    ## specified
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C2184149
    ## living situation
    eventTypes[ 'LivingStatus' ] = umlsConceptType( cui = 'C2184149' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0439044
    ## Living Alone
    eventTypes[ 'alone' ] = umlsConceptType( cui = 'C0439044' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0557130
    ## Lives with family
    eventTypes[ 'with_family' ] = umlsConceptType( cui = 'C0557130' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C3242657
    ## unrelated person
    eventTypes[ 'with_others' ] = umlsConceptType( cui = 'C3242657' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0237154
    ## Homelessness
    eventTypes[ 'homeless' ] = umlsConceptType( cui = 'C0237154' , tui = 'T033' )
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0242271
    ## Employment status
    eventTypes[ 'Employment' ] = umlsConceptType( cui = 'C0242271' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0557351
    ## Employed
    eventTypes[ 'employed' ] = umlsConceptType( cui = 'C0557351' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0041674
    ## Unemployment
    eventTypes[ 'unemployed' ] = umlsConceptType( cui = 'C0041674' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0035345
    ## Retirement
    eventTypes[ 'retired' ] = umlsConceptType( cui = 'C0035345' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0682148
    ## Disability status
    eventTypes[ 'on_disability' ] = umlsConceptType( cui = 'C0682148' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0038492
    ## student (Population Group)
    eventTypes[ 'student' ] = umlsConceptType( cui = 'C0038492' , tui = 'T098' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0555052
    ## homemaker (Professional or Occupational Group)
    eventTypes[ 'homemaker' ] = umlsConceptType( cui = 'C0555052' , tui = 'T097' )
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0001948
    ## Alcohol consumption (Individual Behavior)
    eventTypes[ 'Alcohol' ] = umlsConceptType( cui = 'C0001948' , tui = 'T055' )
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C0281875
    ## illicit drug use (finding)
    eventTypes[ 'Drug' ] = umlsConceptType( cui = 'C0281875' , tui = 'T033' )
    ####################################################
    ## https://uts.nlm.nih.gov/uts/umls/concept/C1287520
    ## Tobacco use and exposure – finding
    eventTypes[ 'Tobacco' ] = umlsConceptType( cui = 'C1287520' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C1971295
    ## TOBACCO NON-USER
    eventTypes[ 'none' ] = umlsConceptType( cui = 'C1971295' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C1698618
    ## Ex-tobacco user
    eventTypes[ 'past' ] = umlsConceptType( cui = 'C1698618' , tui = 'T033' )
    ## https://uts.nlm.nih.gov/uts/umls/concept/C3853727
    ## Tobacco user
    eventTypes[ 'current' ] = umlsConceptType( cui = 'C3853727' , tui = 'T033' )
    ####
    for event_type in eventTypes:
        cas.add( eventTypes[ event_type ] )
    ####
    eventMentions = {}
    modifierMentions = {}
    with open( input_filename , 'r' ) as fp:
        for line in fp:
            line = line.strip()
            ## Continuous:
            ## T1    Organization 0 43    International Business Machines Corporation
            ## Discontinuous (0..23):
            ## T1	Location 0 5;16 23	North America
            ## T1	Location 0 5;8 12;16 23	North America
            ## TODO - add flag to accommodate different scoring styles for
            ##        discontinuous spans.  Current approach treats these
            ##        spans as equivalent to the maximal span of all sub-spans.
            matches = re.match( r'^(T[0-9]+)\s+([\w\-]+)\s+([0-9]+)\s+([0-9]+;[0-9]+\s+)*([0-9]+)\s+(.*)' ,
                                line )
            if( matches ):
                found_tag = matches.group( 2 )
                if( found_tag not in eventTypes and
                    found_tag not in [ 'Duration' ,
                                       'Frequency' ,
                                       'History' ,
                                       'Amount' ,
                                       'Method' ,
                                       'StatusEmploy' ,
                                       'StatusTime' ,
                                       'Type' ,
                                       'TypeLiving' ] ):
                    continue
                mention_id = matches.group( 1 )
                begin_offset = int( matches.group( 3 ) )
                end_offset = int( matches.group( 5 ) )
                text_span = matches.group( 6 )
                if( found_tag in eventTypes ):
                    eventMentions[ mention_id ] = {}
                    eventMentions[ mention_id ][ 'class' ] = found_tag
                    eventMentions[ mention_id ][ 'begin' ] = begin_offset
                    eventMentions[ mention_id ][ 'end' ] = end_offset
                elif( found_tag in [ 'Amount' ,
                                     'Method' ,
                                     'StatusEmploy' ,
                                     'StatusTime' ,
                                     'Type' ,
                                     'TypeLiving' ] ):
                    modifierMentions[ mention_id ] = {}
                    modifierMentions[ mention_id ][ 'role_type' ] = 'Modifier'
                    modifierMentions[ mention_id ][ 'class' ] = found_tag
                    modifierMentions[ mention_id ][ 'begin' ] = begin_offset
                    modifierMentions[ mention_id ][ 'end' ] = end_offset
                elif( found_tag in [ 'Duration' ,
                                     'Frequency' ,
                                     'History' ] ):
                    modifierMentions[ mention_id ] = {}
                    modifierMentions[ mention_id ][ 'role_type' ] = 'TimeMention'
                    modifierMentions[ mention_id ][ 'class' ] = found_tag
                    modifierMentions[ mention_id ][ 'begin' ] = begin_offset
                    modifierMentions[ mention_id ][ 'end' ] = end_offset
                continue
            
            ## Continuous:
            ## A4	StatusTimeVal T12 current
            ## A5	TypeLivingVal T13 with_family
            ## A6	StatusEmployVal T15 homemaker
            matches = re.match( r'^(A[0-9]+)\s+([\w\-]+)\s+(T[0-9]+)\s+(.*)' ,
                                line )
            if( matches ):
                found_tag = matches.group( 2 )
                if( found_tag not in [ 'StatusTimeVal' ,
                                       'StatusEmployVal' ,
                                       'TypeLivingVal' ] ):
                    print( 'Unknown annotation note: {}'.format( found_tag ) )
                    continue
                mention_id = matches.group( 3 )
                annot_val = matches.group( 4 )
                if( found_tag in [ 'StatusEmployVal' ,
                                   'StatusTimeVal' ,
                                   'TypeLivingVal' ] ):
                    modifierMentions[ mention_id ][ found_tag ] = annot_val
                continue
            ############
            ## E1	Tobacco:T1 Status:T2
            ## E2	Alcohol:T3 Status:T4 Amount:T5 Frequency:T6 Type:T10
            matches = re.match( r'^(E[0-9]+)\s+([A-Za-z]+):(T[0-9]+)\s+(.*)' ,
                                line )
            if( matches ):
                found_tag = matches.group( 3 )
                rels = matches.group( 4 ).split( ' ' )
                for relation in rels:
                    rel_entity , rel_tag = relation.split( ':' )
                    rel_entity = rel_entity.strip( '0123456789' )
                    eventMentions[ found_tag ][ rel_entity ] = rel_tag
                continue
        ## We're done extracting all spans and relations
        for event_tag in eventMentions:
            span_class = eventMentions[ event_tag ][ 'class' ]
            ## Main Event
            if( span_class in [ 'Alcohol' , 'Drug' , 'Tobacco' ,
                                'LivingStatus' ] ):
                if( 'Status' not in eventMentions[ event_tag ] ):
                    ## TODO - add explicit warning here
                    continue
                aspect_tag = eventMentions[ event_tag ][ 'Status' ]
                aspect_val = modifierMentions[ aspect_tag ][ 'StatusTimeVal' ]
            ####
            begin_offset = eventMentions[ event_tag ][ 'begin' ]
            end_offset = eventMentions[ event_tag ][ 'end' ]
            ##
            if( span_class in [ 'Employment' ] ):
                if( 'Status' not in eventMentions[ event_tag ] ):
                    ## TODO - add explicit warning here
                    continue
                category_tag = eventMentions[ event_tag ][ 'Status' ]
                category_val = modifierMentions[ category_tag ][ 'StatusEmployVal' ]
            elif( span_class in [ 'LivingStatus' ] ):
                if( 'Type' not in eventMentions[ event_tag ] ):
                    ## TODO - add explicit warning here
                    continue
                category_tag = eventMentions[ event_tag ][ 'Type' ]
                category_val = modifierMentions[ category_tag ][ 'TypeLivingVal' ]
            ################
            ## The default CUI representation for the event is the
            ## parent concept for this domain
            event_cui = eventTypes[ span_class ]
            if( span_class in [ 'Employment' ] ):
                event_cui = eventTypes[ category_val ]
                anEvent = eventType( ontologyConcept = event_cui ,
                                     properties = eventPropertiesType( category = category_val ) )
            elif( span_class in [ 'LivingStatus' ] ):
                event_cui = eventTypes[ category_val ]
                anEvent = eventType( ontologyConcept = event_cui ,
                                     properties = eventPropertiesType( aspect = aspect_val ,
                                                                       category = category_val ) )
            elif( span_class in [ 'Alcohol' , 'Drug' , 'Tobacco' ] ):
                if( span_class in [ 'Tobacco' ] ):
                    event_cui = eventTypes[ aspect_val ]
                anEvent = eventType( ontologyConcept = event_cui ,
                                     properties = eventPropertiesType( aspect = aspect_val ) )
            ## Trigger Event Mention
            anEventMention = eventMentionType( begin = begin_offset ,
                                               end = end_offset ,
                                               ontologyConceptArr = FSArray( elements = [ eventTypes[ span_class ] ] ) ,
                                               event = anEvent )
            ##
            cas.add( anEvent )
            cas.add( anEventMention )
            ####
            triggerArgument = None
            for role_type in [ 'Amount' , 'Method' , 'Status' , 'Type' ,
                               'Duration' , 'Frequency' , 'History' ]:
                if( role_type not in eventMentions[ event_tag ] ):
                    continue
                if( triggerArgument is None ):
                    triggerArgument = relationArgumentType( role = "Trigger" ,
                                                            argument = anEventMention )
                    cas.add( triggerArgument )
                ####
                role_tag = eventMentions[ event_tag ][ role_type ]
                if( modifierMentions[ role_tag ][ 'role_type' ] == 'Modifier' ):
                    roleMention = modifierType( begin = modifierMentions[ role_tag ][ 'begin' ] ,
                                                end = modifierMentions[ role_tag ][ 'end' ] )
                elif( modifierMentions[ role_tag ][ 'role_type' ] == 'TimeMention' ):
                    roleMention = timeMentionType( begin = modifierMentions[ role_tag ][ 'begin' ] ,
                                                   end = modifierMentions[ role_tag ][ 'end' ] )
                else:
                    print( 'Surprising role_type: {}'.format( modifierMentions[ role_tag ][ 'role_type' ] ) )
                    continue
                dependentArgument = relationArgumentType( role = role_type ,
                                                          argument = roleMention )
                dependentRelation = binaryTextRelationType( arg1 = triggerArgument ,
                                                            arg2 = dependentArgument )
                cas.add_all( [ roleMention ,
                               dependentArgument ,
                               dependentRelation ] )
    return( cas )


if __name__ == "__main__":
    ##
    args = init_args()
    ##
    typesystem = loadTypesystem( args )
    ##
    ############################
    ## Iterate over the files, covert to CAS, and write the XMI to disk
    file_list = [ os.path.basename( f ) for f in glob.glob( os.path.join( args.brat_root ,
                                                                          '*.ann' ) ) ]
    for brat_filename in tqdm( sorted( file_list ) ,
                               file = args.progressbar_file ,
                               disable = args.progressbar_disabled ):
        plain_filename = brat_filename[ 0:-4 ]
        txt_path = os.path.join( args.txt_root ,
                                '{}.txt'.format( plain_filename ) )
        cas_path = os.path.join( args.cas_root ,
                                 '{}.xmi'.format( plain_filename ) )
        if( not os.path.exists( txt_path ) ):
            log.warn( 'No matching txt file found for \'{}\''.format( xml_filename ) )
            continue
        with open( txt_path , 'r' ) as fp:
            note_contents = fp.read().strip()
        cas = cassis.Cas( typesystem = typesystem )
        cas.sofa_string = note_contents
        cas.sofa_mime = "text/plain"
        cas = process_ann_file( cas ,
                                os.path.join( args.brat_root , brat_filename ) )
        cas.to_xmi( path = cas_path ,
                    pretty_print = True )

            
