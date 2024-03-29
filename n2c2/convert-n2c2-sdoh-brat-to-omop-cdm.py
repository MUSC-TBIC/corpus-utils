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

import warnings

warnings.filterwarnings( 'ignore' , category = UserWarning , module = 'cassis' )

#############################################
## helper functions
#############################################

def initialize_arg_parser():
    parser = argparse.ArgumentParser( description = """
""")
    parser.add_argument( '-v' , '--verbose' ,
                         help = "print more information" ,
                         action = "store_true" )

    parser.add_argument( '--append' ,
                         help = "Append new lexical entries to pre-existing lexicons" ,
                         action = "store_true" )

    parser.add_argument( '--allow-relations' ,
                         dest = 'allowRels' ,
                         help = "Allow relation arcs in source documents to be passed through (Default. Including is a noop)" ,
                         action = "store_true" )

    parser.add_argument( '--no-relations' ,
                         dest = 'noRels' ,
                         help = "Do not create any relation arcs between concepts" ,
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
                         dest = "cas_root",
                         help = "Directory for output corpus in CAS XMI formatted XML" )

    parser.add_argument( '--lxcn-root' , default = None ,
                         dest = "lxcn_root",
                         help = "Directory for output tab-delimited lexicon files" )

    parser.add_argument( '--normalization' ,
                         dest = 'normalization' ,
                         default = 'lowercase' ,
                         choices = [ 'none' , 'lowercase' , 'digits' ] ,
                         help = "Normalization process to perform on lexical entries" )

    parser.add_argument( '--min-term-length' , default = 0 ,
                         dest = 'minTermLength' ,
                         help = "Minimum character count for a lexical item to be included in generated lexicons (0 means to allow all terms)" )

    parser.add_argument( '--gap-file' , default = None ,
                         dest = "gapFile",
                         help = "CSV file for listing distances between triggers and modifiers" )
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
    if( args.cas_root is not None and
        not os.path.exists( args.cas_root ) ):
        try:
            os.makedirs( args.cas_root )
        except OSError as e:
            log.error( 'OSError caught while trying to create CAS XMI output folder:  {}'.format( e ) )
        except IOError as e:
            log.error( 'IOError caught while trying to create CAS XMI output folder:  {}'.format( e ) )
    if( args.lxcn_root is not None and
        not os.path.exists( args.lxcn_root ) ):
        try:
            os.makedirs( args.lxcn_root )
        except OSError as e:
            log.error( 'OSError caught while trying to create lexicon output folder:  {}'.format( e ) )
        except IOError as e:
            log.error( 'IOError caught while trying to create lexicon output folder:  {}'.format( e ) )
    ####
    if( args.gapFile is not None ):
        with open( args.gapFile , 'w' ) as fp:
            fp.write( '{}\t{}\t{}\n'.format( 'Trigger' , 'Relation' , 'Distance' ) )
    ####
    try:
        args.minTermLength = int( args.minTermLength )
    except ValueError:
        log.error( 'Min term length value is not an int:  "{}"'.format( args.minTermLength ) )
    ########
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
    ############
    ## ... for OMOP CDM v5.3 FACT_RELATIONSHIP table properties
    ##     https://ohdsi.github.io/CommonDataModel/cdm53.html#FACT_RELATIONSHIP
    FactRelationship = typesystem.create_type( name = 'edu.musc.tbic.omop_cdm.Fact_Relationship_TableProperties' ,
                                               supertypeName = 'uima.tcas.Annotation' )
    typesystem.create_feature( domainType = FactRelationship ,
                               name = 'domain_concept_id_1' ,
                               description = 'The CONCEPT id for the appropriate scoping domain' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = FactRelationship ,
                               name = 'fact_id_1' ,
                               description = 'The id for the first fact' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = FactRelationship ,
                               name = 'domain_concept_id_2' ,
                               description = 'The CONCEPT id for the appropriate scoping domain' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = FactRelationship ,
                               name = 'fact_id_2' ,
                               description = 'The id for the second fact' ,
                               rangeType = 'uima.cas.Integer' )
    typesystem.create_feature( domainType = FactRelationship ,
                               name = 'relationship_concept_id' ,
                               description = 'This id for the relationship held between the two facts' ,
                               rangeType = 'uima.cas.Integer' )
    ####
    return( typesystem )


def normalizeTerm( word , normalization = 'lowercase' ):
    lemma = word
    if( normalization in [ 'lowercase' , 'digits' ] ):
        lemma = lemma.lower()
    if( normalization in [ 'digits' ] ):
        ## Escape all special regex characters
        lemma = re.sub( '\+' , '.' , lemma )
        lemma = re.sub( '\?' , '.' , lemma )
        lemma = re.sub( '\*' , '.' , lemma )
        lemma = re.sub( '\[' , '.' , lemma )
        lemma = re.sub( '\]' , '.' , lemma )
        lemma = re.sub( '\(' , '.' , lemma )
        lemma = re.sub( '\)' , '.' , lemma )
        ## Replace digits with \d+ regex
        lemma = re.sub( r' \d+ ' , ' \\\d+ ' , lemma )
        lemma = re.sub( r' \d+ ' , ' \\\d+ ' , lemma )
        lemma = re.sub( r'^\d+ ' , '\\\d+ ' , lemma )
        lemma = re.sub( r' \d+$' , ' \\\d+' , lemma )
    return( lemma )


noteNlp_typeString = 'edu.musc.tbic.omop_cdm.Note_Nlp_TableProperties'
factRelationship_typeString = 'edu.musc.tbic.omop_cdm.Fact_Relationship_TableProperties'

#############################################
## core functions
#############################################

lexicon = {}
relPairs = { 'IsTriggerFor' : 'HasTrigger' ,
             'HasStatus' : 'IsStatusFor' ,
             'HasStatusEmploy' : 'IsStatusEmployFor' ,
             'HasStatusTime' : 'IsStatusTimeFor' ,
             'HasDuration' : 'IsDurationFor' ,
             'HasHistory' : 'IsHistoryFor' ,
             'HasType' : 'IsTypeFor' ,
             'HasTypeLiving' : 'IsTypeLivingFor' ,
             'HasMethod' : 'IsMethodFor' ,
             'HasAmount' : 'IsAmountFor' ,
             'HasFrequency' : 'IsFrequencyFor' 
            }
relIds = {}
count = 0
## Make sure all relations are symmetrical
## TODO - add relIds mapping to metadata in CAS XMI
for relA in [ 'IsTriggerFor' ,
              'HasStatus' ,
              'HasStatusEmploy' ,
              'HasStatusTime' ,
              'HasDuration' ,
              'HasHistory' , 
              'HasType' ,
              'HasTypeLiving' ,
              'HasMethod' ,
              'HasAmount' ,
              'HasFrequency' ]:
    count += 1
    relIds[ relA ] = count
    count += 1
    relIds[ relPairs[ relA ] ] = count
    relPairs[ relPairs[ relA ] ] = relA

def process_ann_file( cas ,
                      input_filename ,
                      note_total ,
                      note_count ,
                      normalization = 'lowercase' ,
                      min_term_length = 0 ,
                      skip_relations = False ,
                      gap_file = None ):
    ########
    spans = {}
    ##
    FSArray = typesystem.get_type( 'uima.cas.FSArray' )
    
    noteNlpType = typesystem.get_type( noteNlp_typeString )
    factRelationshipType = typesystem.get_type( factRelationship_typeString )
    
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
    ####
    eventMentions = {}
    modifierMentions = {}
    relationArcs = {}
    with open( input_filename , 'r' ) as fp:
        try:
            note_id = int( os.path.basename( input_filename )[ 0:-4 ] )
        except ValueError as e:
            note_id = note_count
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
                if( found_tag not in eventConcepts and
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
                middle_offset = matches.group( 4 )
                end_offset = int( matches.group( 5 ) )
                text_span = matches.group( 6 )
                lc_text_span = normalizeTerm( text_span ,
                                              normalization = normalization )
                if( found_tag not in lexicon ):
                    lexicon[ found_tag ] = {}
                if( min_term_length == 0 or
                    len( lc_text_span ) >= min_term_length ):
                    if( lc_text_span not in lexicon[ found_tag ] ):
                        lexicon[ found_tag ][ lc_text_span ] = {}
                    if( text_span not in lexicon[ found_tag ][ lc_text_span ] ):
                        lexicon[ found_tag ][ lc_text_span ][ text_span ] = 0
                    lexicon[ found_tag ][ lc_text_span ][ text_span ] += 1
                ########
                if( found_tag in eventConcepts ):
                    eventMentions[ mention_id ] = {}
                    eventMentions[ mention_id ][ 'class' ] = found_tag
                    eventMentions[ mention_id ][ 'begin' ] = begin_offset
                    eventMentions[ mention_id ][ 'end' ] = end_offset
                    eventMentions[ mention_id ][ 'text' ] = text_span
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
                    modifierMentions[ mention_id ][ 'text' ] = text_span
                elif( found_tag in [ 'Duration' ,
                                     'Frequency' ,
                                     'History' ] ):
                    modifierMentions[ mention_id ] = {}
                    modifierMentions[ mention_id ][ 'role_type' ] = 'TimeMention'
                    modifierMentions[ mention_id ][ 'class' ] = found_tag
                    modifierMentions[ mention_id ][ 'begin' ] = begin_offset
                    modifierMentions[ mention_id ][ 'end' ] = end_offset
                    modifierMentions[ mention_id ][ 'text' ] = text_span
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
                    if( found_tag not in lexicon ):
                        lexicon[ found_tag ] = {}
                    text_span = modifierMentions[ mention_id ][ 'text' ]
                    lc_text_span = normalizeTerm( text_span ,
                                                  normalization = normalization )
                    if( lc_text_span not in lexicon[ found_tag ] ):
                        lexicon[ found_tag ][ lc_text_span ] = {}
                    if( annot_val not in lexicon[ found_tag ][ lc_text_span ] ):
                        lexicon[ found_tag ][ lc_text_span ][ annot_val ] = 0
                    lexicon[ found_tag ][ lc_text_span ][ annot_val ] += 1
                continue
            ############
            ## E1	Tobacco:T1 Status:T2
            ## E2	Alcohol:T3 Status:T4 Amount:T5 Frequency:T6 Type:T10
            matches = re.match( r'^(E[0-9]+)\s+([A-Za-z]+):(T[0-9]+)\s+(.*)' ,
                                line )
            if( matches ):
                trigger_type = matches.group( 2 )
                found_tag = matches.group( 3 )
                trigger_id = found_tag.strip( 'T' )
                rels = matches.group( 4 ).split( ' ' )
                for relation in rels:
                    rel_entity , rel_tag = relation.split( ':' )
                    rel_id = rel_tag.strip( 'T' )
                    ## TODO - handle multiple relations arcs for a
                    ## given type (e.g., "Amount", "Amount2",
                    ## "Amount3", etc.)
                    rel_entity = rel_entity.strip( '0123456789' )
                    eventMentions[ found_tag ][ rel_entity ] = rel_tag
                    ########
                    if( gap_file is not None ):
                        try:
                            begin_trigger = eventMentions[ 'T{}'.format( trigger_id ) ][ 'begin' ]
                            end_trigger = eventMentions[ 'T{}'.format( trigger_id ) ][ 'end' ]
                            begin_modifier = modifierMentions[ 'T{}'.format( rel_id ) ][ 'begin' ]
                            end_modifier = modifierMentions[ 'T{}'.format( rel_id ) ][ 'end' ]
                            if( begin_trigger == begin_modifier ):
                                distance = 0
                            elif( end_trigger < begin_modifier ):
                                distance = begin_modifier - end_trigger
                            else:
                                distance = begin_trigger - end_modifier
                            with open( gap_file , 'a' ) as fp:
                                fp.write( '{}\t{}\t{}\n'.format( trigger_type , rel_entity , distance ) )
                        except KeyError as e:
                            ## we can skip it
                            1
                    ########
                    if( trigger_id not in relationArcs ):
                        relationArcs[ trigger_id ] = {}
                    if( rel_entity not in relationArcs[ trigger_id ] ):
                        relationArcs[ trigger_id ][ rel_entity ] = set()
                    if( rel_id not in relationArcs ):
                        relationArcs[ rel_id ] = {}
                    if( rel_entity not in relationArcs[ rel_id ] ):
                        relationArcs[ rel_id ][ rel_entity ] = set()
                    ####
                    relationArcs[ trigger_id ][ rel_entity ].add( rel_id )
                    relationArcs[ rel_id ][ rel_entity ].add( trigger_id )
                    ## TODO - make look-up in real OMOP CDM concept table easier
                    triggerRelType = relIds[ 'Has{}'.format( rel_entity ) ]
                    relTriggerType = relIds[ 'Is{}For'.format( rel_entity ) ]
                    if( not skip_relations ):
                        triggerRelRelation = factRelationshipType( domain_concept_id_1 = 1 ,
                                                                   fact_id_1 = trigger_id ,
                                                                   domain_concept_id_2 = 2 ,
                                                                   fact_id_2 = rel_id ,
                                                                   relationship_concept_id = triggerRelType )
                        cas.add( triggerRelRelation )
                        relTriggerType = relIds[ 'Is{}For'.format( rel_entity ) ]
                        relTriggerRelation = factRelationshipType( domain_concept_id_2 = 1 ,
                                                                   fact_id_2 = trigger_id ,
                                                                   domain_concept_id_1 = 2 ,
                                                                   fact_id_1 = rel_id ,
                                                                   relationship_concept_id = relTriggerType )
                        cas.add( relTriggerRelation )
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
            text_span = eventMentions[ event_tag ][ 'text' ]
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
            ####
            term_exists = 'y'
            term_temporal = ''
            modifiers = []
            if( span_class in [ 'Employment' ] ):
                modifiers.append( 'StatusVal={}'.format( category_val ) )
            elif( span_class in [ 'LivingStatus' ] ):
                if( aspect_val in [ 'past' , 'future' ] ):
                    term_exists = 'n'
                term_temporal = aspect_val
                modifiers.append( 'StatusVal={}'.format( aspect_val ) )
                modifiers.append( 'TypeVal={}'.format( category_val ) )
            elif( span_class in [ 'Alcohol' , 'Drug' , 'Tobacco' ] ):
                if( aspect_val in [ 'none' , 'past' ] ):
                    term_exists = 'n'
                term_temporal = aspect_val
                modifiers.append( 'TriggerVal={}'.format( span_class ) )
                modifiers.append( 'StatusVal={}'.format( aspect_val ) )
            ########
            note_nlp_id = event_tag.strip( 'T' )
            for role_type in [ 'Amount' , 'Method' , 'Status' , 'Type' ,
                               'Duration' , 'Frequency' , 'History' ]:
                if( role_type not in eventMentions[ event_tag ] ):
                    continue
                ####
                role_tag = eventMentions[ event_tag ][ role_type ]
                role_id = role_tag.strip( 'T' )
                role_cui = ''
                role_modifiers = []
                if( not skip_relations ):
                    role_modifiers.append( '{}={}'.format( 'Trigger' ,
                                                           note_nlp_id ) )
                    modifiers.append( '{}={}'.format( role_type ,
                                                      role_id ) )
                if( span_class in [ 'Employment' ] ):
                    if( role_type == 'Status' ):
                        role_cui = eventConcepts[ category_val ]
                        role_modifiers.append( '{}={}'.format( 'StatusVal' ,
                                                               category_val ) )
                elif( span_class in [ 'LivingStatus' ] ):
                    if( role_type == 'Status' ):
                        role_cui = modifierMentions[ role_tag ][ 'StatusTimeVal' ]
                        role_modifiers.append( '{}={}'.format( 'StatusVal' ,
                                                               aspect_val ) )
                    elif( role_type == 'Type' ):
                        role_cui = eventConcepts[ category_val ]
                        role_modifiers.append( '{}={}'.format( 'TypeVal' ,
                                                               category_val ) )
                elif( span_class in [ 'Tobacco' ] ):
                    if( role_type == 'Status' ):
                        role_cui = eventConcepts[ aspect_val ]
                        role_modifiers.append( '{}={}'.format( 'StatusVal' ,
                                                               aspect_val ) )
            ## Trigger Event Mention
            anEventMention = noteNlpType( note_nlp_id = note_nlp_id ,
                                          note_id = note_id ,
                                          begin = begin_offset ,
                                          end = end_offset ,
                                          offset = begin_offset ,
                                          lexical_variant = text_span ,
                                          nlp_system = 'Reference Standard' ,
                                          note_nlp_source_concept_id = eventConcepts[ span_class ] ,
                                          term_exists = term_exists ,
                                          term_temporal = term_temporal ,
                                          term_modifiers = ';'.join( modifiers ) )
            cas.add( anEventMention )
        ######## Now tackel the modifiers
        for role_tag in modifierMentions:
            role_type = modifierMentions[ role_tag ][ 'class' ]
            role_id = role_tag.strip( 'T' )
            role_modifiers = []
            begin_offset = modifierMentions[ role_tag ][ 'begin' ]
            end_offset = modifierMentions[ role_tag ][ 'end' ]
            text_span = modifierMentions[ role_tag ][ 'text' ]
            cui_source = None
            if( role_type == 'StatusTime' ):
                cui_source = 'StatusTimeVal'
            elif( role_type == 'StatusEmploy' ):
                cui_source = 'StatusEmployVal'
            elif( role_type == 'TypeLiving' ):
                cui_source = 'TypeLivingVal'
            if( cui_source is None ):
                role_cui = role_type
            else:
                role_cui = modifierMentions[ role_tag ][ cui_source ]
            roleMention = noteNlpType( note_nlp_id = role_id ,
                                       note_id = note_id ,
                                       begin = begin_offset ,
                                       end = end_offset ,
                                       offset = begin_offset ,
                                       lexical_variant = text_span ,
                                       nlp_system = 'Reference Standard' ,
                                       note_nlp_source_concept_id = role_cui ,
                                       ##term_exists = '' ,
                                       ##term_temporal = '' ,
                                       term_modifiers = ';'.join( role_modifiers ) )
            cas.add( roleMention )
    #################################
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
    note_total = len( file_list )
    note_count = 0
    for brat_filename in tqdm( sorted( file_list ) ,
                               file = args.progressbar_file ,
                               disable = args.progressbar_disabled ):
        plain_filename = brat_filename[ 0:-4 ]
        txt_path = os.path.join( args.txt_root ,
                                '{}.txt'.format( plain_filename ) )
        if( not os.path.exists( txt_path ) ):
            log.warn( 'No matching txt file found for \'{}\''.format( xml_filename ) )
            continue
        with open( txt_path , 'r' ) as fp:
            note_contents = fp.read().strip()
        cas = cassis.Cas( typesystem = typesystem )
        cas.sofa_string = note_contents
        cas.sofa_mime = "text/plain"
        note_count += 1
        cas = process_ann_file( cas ,
                                os.path.join( args.brat_root , brat_filename ) ,
                                note_total = note_total ,
                                note_count = note_count ,
                                normalization = args.normalization ,
                                min_term_length = args.minTermLength ,
                                skip_relations = args.noRels ,
                                gap_file = args.gapFile )
        if( args.cas_root is not None ):
            cas_path = os.path.join( args.cas_root ,
                                     '{}.xmi'.format( plain_filename ) )
            cas.to_xmi( path = cas_path ,
                        pretty_print = True )
    ####
    if( args.lxcn_root is not None ):
        for entity in lexicon:
            if( entity in [ 'StatusEmployVal' ,
                            'StatusTimeVal' ,
                            'TypeLivingVal' ] ):
                continue
            file_access_flag = 'w'
            if( args.append ):
                file_access_flag = 'a'                    
            with open( os.path.join( args.lxcn_root ,
                                     '{}.lxcn'.format( entity ) ) ,
                       file_access_flag ) as fp:
                count = 0
                for lexeme in sorted( lexicon[ entity ] ):
                    prefix = '\t'
                    ambiguity = []
                    default_value = None
                    default_count = 0
                    if( entity in [ 'StatusEmploy' , 'StatusTime' , 'TypeLiving' ] ):
                        if( entity == 'StatusEmploy' ):
                            value_concept = 'StatusEmployVal'
                        elif( entity == 'StatusTime' ):
                            value_concept = 'StatusTimeVal'
                        elif( entity == 'TypeLiving' ):
                            value_concept = 'TypeLivingVal'
                        for annot_val in lexicon[ value_concept ][ lexeme ]:
                            ambiguity.append( '{}={}'.format( annot_val ,
                                                              lexicon[ value_concept ][ lexeme ][ annot_val ] ) )
                            if( lexicon[ value_concept ][ lexeme ][ annot_val ] > default_count ):
                                default_value = annot_val
                    ## This check may seem weird now but it was useful
                    ## for early testing.  I'm keeping it around for a
                    ## spell in case it proves useful again.
                    if( len( lexicon[ entity ][ lexeme ] ) > 0 ):
                        prefix = '\t\t'
                        if( default_value is None ):
                            fp.write( '{}\n'.format( lexeme ) )
                        else:
                            fp.write( '{}\t{}\n'.format( lexeme , default_value ) )
                        ##if( count < 5 ):
                        ##    print( '\t{}\t\t{}'.format( lexeme , '|'.join( ambiguity ) ) )
                        ambiguity = []
                    for instance in sorted( lexicon[ entity ][ lexeme ] ):
                        ##if( count < 5 ):
                        ##    print( '{}{}\t{}\t{}'.format( prefix , instance , lexicon[ entity ][ lexeme ][ instance ] ,
                        ##                                  '|'.join( ambiguity ) ) )
                        count += 1

            
