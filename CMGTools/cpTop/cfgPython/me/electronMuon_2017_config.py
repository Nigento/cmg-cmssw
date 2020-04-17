import os
import ROOT

import PhysicsTools.HeppyCore.framework.config as cfg
from PhysicsTools.HeppyCore.framework.config import printComps
from PhysicsTools.HeppyCore.framework.heppy_loop import getHeppyOption
from PhysicsTools.HeppyCore.framework.looper import Looper
from PhysicsTools.HeppyCore.framework.event import Event
Event.print_patterns = ['*taus*', 
                        '*muons*', 
                        '*electrons*', 
                        'veto_*',  
                        '*jets*']

#import pdb; pdb.set_trace()

from CMGTools.RootTools.samples.ComponentCreator import ComponentCreator
#ComponentCreator.useAAA = True
ComponentCreator.useLyonAAA = True

from CMGTools.H2TauTau.heppy.analyzers.Cleaner import Cleaner


import logging
logging.shutdown()
#reload(logging)
logging.basicConfig(level=logging.WARNING)



############################################################################
# Options
############################################################################

# Get all heppy options; set via "-o production" or "-o production=True"

# production = True run on batch, production = False run locally
test = getHeppyOption('test', True)
syncntuple = getHeppyOption('syncntuple', True)
data = getHeppyOption('data', True)
tes_string = getHeppyOption('tes_string', '') # '_tesup' '_tesdown'
reapplyJEC = getHeppyOption('reapplyJEC', True)


############################################################################
# Components
############################################################################
from CMGTools.cpTop.proto.samples.fall17.ttbar2017 import mc_ttbar
from CMGTools.cpTop.proto.samples.fall17.ttbar2017 import mc_singletop
from CMGTools.cpTop.proto.samples.fall17.ttbar2017 import data_elecmuon
from CMGTools.cpTop.proto.samples.fall17.trigger import data_triggers
from CMGTools.cpTop.proto.samples.fall17.trigger import mc_triggers

events_to_pick = []

# Global Tag
gt_mc = 'Fall17_17Nov2017_V32_MC'
gt_data = 'Fall17_17Nov2017{}_V32_DATA'
#https://twiki.cern.ch/twiki/bin/view/CMS/JECDataMC


# PileUp
puFileData = '$CMSSW_BASE/src/CMGTools/cpTop/data/pudistributions_data_2017.root'
puFileMC = '$CMSSW_BASE/src/CMGTools/cpTop/data/pileup.root'

for sample in mc_singletop:
    sample.triggers = mc_triggers
    sample.puFileMC = puFileMC
    sample.puFileData = puFileData
 
for sample in data_elecmuon:
    # sample.name[sample.name.find('2017')+4] are era A,B,C,D,E and F
    sample.triggers = data_triggers[sample.name[sample.name.find('2017')+4]]
    era = sample.name[sample.name.find('2017')+4]
    if 'V32' in gt_data and era in ['D','E']:
        era = 'DE'
    sample.dataGT = gt_data.format(era)

if (not data):
    selectedComponents = mc_singletop
    print("Not data")
elif (data):
    selectedComponents = data_elecmuon
    print("Data")

############################################################################
# Test
############################################################################
import CMGTools.cpTop.proto.samples.fall17.ttbar2017 as backgrounds_forindex
from CMGTools.cpTop.proto.samples.component_index import ComponentIndex
bindex = ComponentIndex( backgrounds_forindex)

if test:
    cache = True
    if (not data):
        comp = bindex.glob('MC_a_dilep')[0]
    else:
        comp = selectedComponents[9]
    selectedComponents = [comp]
    comp.files = [comp.files[0]]#10 bug on semilep
    comp.splitFactor = 1
    comp.fineSplitFactor = 1


############################################################################
# Analyzers 
############################################################################
from PhysicsTools.Heppy.analyzers.core.JSONAnalyzer import JSONAnalyzer
from PhysicsTools.Heppy.analyzers.core.SkimAnalyzerCount import SkimAnalyzerCount
from CMGTools.cpTop.proto.analyzers.TriggerAnalyzer import TriggerAnalyzer
from PhysicsTools.Heppy.analyzers.objects.VertexAnalyzer import VertexAnalyzer
from CMGTools.cpTop.heppy.analyzers.Debugger import Debugger

json = cfg.Analyzer(JSONAnalyzer,
                    name='JSONAnalyzer',)

skim = cfg.Analyzer(SkimAnalyzerCount,
                    name='SkimAnalyzerCount')

trigger = cfg.Analyzer(TriggerAnalyzer,
                       name='TriggerAnalyzer',
                       addTriggerObjects=True,
                       requireTrigger=False,
                       usePrescaled=False)

vertex = cfg.Analyzer(VertexAnalyzer,
                      name='VertexAnalyzer',
                      fixedWeight=1,
                      keepFailingEvents=False,
                      verbose=False)


debugger = cfg.Analyzer(Debugger,
                        name = 'Debugger',
                        condition = lambda x: True)

############################################################################
# Muon 
############################################################################
# setting up an alias for our isolation, now use iso_htt everywhere
from PhysicsTools.Heppy.physicsobjects.Muon import Muon
from CMGTools.cpTop.heppy.analyzers.MuonSFARC import MuonSFARC
from CMGTools.cpTop.heppy.analyzers.MuonAnalyzer import MuonAnalyzer
from CMGTools.cpTop.heppy.analyzers.EventFilter import EventFilter
from CMGTools.cpTop.heppy.analyzers.Selector import Selector

Muon.iso_htt = lambda x: x.relIso(0.4, 
                                  'dbeta', 
                                  dbeta_factor = 0.5, 
                                  all_charged = False)

muons = cfg.Analyzer(MuonAnalyzer,
                     name = 'MuonAnalyzer',
                     output = 'muons',
                     muons = 'slimmedMuons',)

def select_muon_function(muon): #boolean use to select good muons
    return muon.pt() > 26 and \
           abs(muon.eta()) < 2.4 and\
           muon.tightId() and\
           muon.iso_htt() < 0.15 
    # https://twiki.cern.ch/twiki/bin/view/CMS/SWGuideMuonIdRun2

def exclude_muon_function(muon):
    return muon.pt() > 10 and \
           abs(muon.eta()) < 2.5 and\
           muon.looseId() and\
           muon.iso_htt() < 0.25 and\
           not(select_muon_function(muon))

select_muon = cfg.Analyzer(Selector,
                           'select_muon',
                           output = 'select_muon',
                           src = 'muons',
                           filter_func = select_muon_function)

exclude_muon = cfg.Analyzer(Selector,
                           'exclude_muon',
                           output = 'exclude_muon',
                           src = 'muons',
                           filter_func = exclude_muon_function)

reweight_muon = cfg.Analyzer(MuonSFARC, 
                             'reweight_muon', 
                             muons = 'select_muon')

one_muon = cfg.Analyzer(EventFilter, 
                        'one_muon',
                        src = 'select_muon',
                        filter_func = lambda x : len(x)>0)
                        
exclude_loose_muon = cfg.Analyzer(EventFilter,
                                 'exlude_loose_muon',
                                 src='exclude_muon',
                                 filter_func = lambda x : len(x)==0)
                        
############################################################################
# Electron 
############################################################################
# setting up an alias for our isolation, now use iso_htt everywhere
from PhysicsTools.Heppy.physicsobjects.Electron import Electron
from PhysicsTools.Heppy.physicsutils.EffectiveAreas import areas
from CMGTools.cpTop.heppy.analyzers.ElectronSFARC import ElectronSFARC
from CMGTools.cpTop.heppy.analyzers.ElectronAnalyzer import ElectronAnalyzer
from CMGTools.cpTop.heppy.analyzers.EventFilter import EventFilter
from CMGTools.cpTop.heppy.analyzers.Selector import Selector

Electron.EffectiveArea03 = areas['Fall17']['electron']

Electron.iso_htt = lambda x: x.relIso(0.3,
                                      "EA", #effective area
                                      all_charged=False)

electrons = cfg.Analyzer(ElectronAnalyzer,
                         output = 'electrons',
                         electrons = 'slimmedElectrons',) #name in MiniAOD


def is_out_gap_ECAL(electron):
    return abs(electron.superCluster().eta()) >= 2.5 or\
           abs(electron.superCluster().eta()) <= 1.479

def select_electron_function(electron): #function use in the next Analyzer
    return electron.pt() > 35 and\
           abs(electron.eta()) < 1.479 and\
           is_out_gap_ECAL(electron) and\
           electron.id_passes("cutBasedElectronID-Fall17-94X-V2","tight") 
           
def exclude_electron_function(electron): #function use in the next Analyzer
    return electron.pt() > 15 and\
           abs(electron.eta()) < 2.5 and\
           is_out_gap_ECAL(electron) and\
           electron.id_passes("cutBasedElectronID-Fall17-94X-V2","veto") and\
           not(select_electron_function(electron))

select_electron = cfg.Analyzer(Selector,
                               'select_electron',
                               output = 'select_electron',
                               src = 'electrons',
                               filter_func = select_electron_function)

exclude_electron = cfg.Analyzer(Selector,
                              'exclude_electron',
                              output = 'exclude_electron',
                              src = 'electrons',
                              filter_func = exclude_electron_function)
                         
reweight_electron = cfg.Analyzer(ElectronSFARC, 
                                 'reweight_electron', 
                                 electrons = 'select_electron')
                               
one_electron = cfg.Analyzer(EventFilter, 
                            'one_electron',
                            src = 'select_electron',
                            filter_func = lambda x : len(x)>0)

exclude_loose_electron = cfg.Analyzer(EventFilter,
                                     'exclude_loose_electron',
                                     src='exclude_electron',
                                     filter_func = lambda x : len(x)==0)
 
############################################################################
# Jets 
############################################################################
from CMGTools.cpTop.heppy.analyzers.JetAnalyzer import JetAnalyzer
from CMGTools.cpTop.heppy.analyzers.JetCleaner import JetCleaner
from CMGTools.cpTop.heppy.analyzers.EventFilter import EventFilter


def select_good_jets_FixEE2017(jet): #function use in the next Analyzer
    return jet.correctedJet("Uncorrected").pt() > 20 and abs(jet.eta()) < 4.7

jets = cfg.Analyzer(JetAnalyzer, 
                    output = 'jets',
                    jets = 'slimmedJets',
                    do_jec = True,
                    gt_mc = gt_mc,
                    selection = select_good_jets_FixEE2017)

# From https://twiki.cern.ch/twiki/bin/view/CMS/JetID13TeVRun2017
def select_jets_IDpt(jet): #function use in the next Analyzer
    return  jet.pt()>20 and\
            abs(jet.eta())<2.4 and\
            jet.jetID("PAG_ttbarID_Loose")

jets_20_unclean = cfg.Analyzer(Selector,
                               'jets_20_unclean',
                               output = 'jets_20_unclean',
                               src = 'jets',
                               filter_func = select_jets_IDpt)

jet_20_electron_clean = cfg.Analyzer(JetCleaner,
                      output = 'jets_20_electron_clean',
                      leptons = 'select_electron',
                      jets = 'jets_20_unclean',
                      drmin = 0.4)
                      
jet_20_clean = cfg.Analyzer(JetCleaner,
                      output = 'jets_20_clean',
                      leptons = 'select_muon',
                      jets = 'jets_20_electron_clean',
                      drmin = 0.4)

jets_40 = cfg.Analyzer(Selector,
                       'jets_40',
                       output = 'jets_40',
                       src = 'jets_20_clean',
                       filter_func = lambda x : x.pt()>40)


three_jets = cfg.Analyzer(EventFilter, 
                        name = 'ThreeJets',
                        src = 'jets_40',
                        filter_func = lambda x : 4>len(x) >1)

############################################################################
# b-Jets 
############################################################################
from CMGTools.cpTop.heppy.analyzers.BJetAnalyzerARC import BJetAnalyzerARC
from CMGTools.cpTop.heppy.analyzers.EventFilter import EventFilter


btagger = cfg.Analyzer(BJetAnalyzerARC, 
                       'btagger', 
                       jets = 'jets_40')

one_bjets = cfg.Analyzer(EventFilter, 
                         name = 'OneBJets',
                         src = 'bjets_60',
                         filter_func = lambda x : 3>len(x)>=0)

#always put after btagger
bjets_60 = cfg.Analyzer(Selector, 
                        'bjets_60',
                        output ='bjets_60', 
                        src = 'jets_40',
                        filter_func = lambda x: x.is_btagged and x.pt()>60)

############################################################################
# Generator stuff 
############################################################################
from PhysicsTools.Heppy.analyzers.gen.LHEWeightAnalyzer import LHEWeightAnalyzer
from PhysicsTools.Heppy.analyzers.core.PileUpAnalyzer import PileUpAnalyzer
from CMGTools.cpTop.heppy.analyzers.MCWeighter import MCWeighter
from CMGTools.cpTop.proto.analyzers.NJetsAnalyzer import NJetsAnalyzer
from CMGTools.cpTop.heppy.analyzers.METAnalyzer import METAnalyzer
from CMGTools.cpTop.heppy.analyzers.GenAnalyzer import GenAnalyzer
from CMGTools.cpTop.heppy.analyzers.RegionAnalyzer import RegionAnalyzer

pfmetana = cfg.Analyzer(METAnalyzer,
                        name='PFMetana',
                        recoil_correction_file='HTT-utilities/RecoilCorrections/data/Type1_PFMET_2017.root',
                        met = 'pfmet',
                        apply_recoil_correction= True,#Recommendation states loose pfjetID for jet multiplicity but this WP is not supported anymore?
                        runFixEE2017= True)

lheweight = cfg.Analyzer(LHEWeightAnalyzer,
                         name="LHEWeightAnalyzer",
                         useLumiInfo=False)

pileup = cfg.Analyzer(PileUpAnalyzer,
                      name='PileUpAnalyzer',
                      true=True,
                      autoPU=False)

mcweighter = cfg.Analyzer(MCWeighter,
                          'MCWeighter')

njets_ana = cfg.Analyzer(NJetsAnalyzer,
                         name='NJetsAnalyzer',
                         fillTree=True,
                         verbose=False)

region_ana = cfg.Analyzer(RegionAnalyzer,
			  'regionAnalyzer',
			  jets='jets_40',
			  bjets_60='bjets_60')


############################################################################
# Ntuples 
############################################################################
from CMGTools.cpTop.heppy.analyzers.NtupleProducer import NtupleProducer
from CMGTools.cpTop.heppy.ntuple.NtupleCreator import common as event_content_test

ntuple = cfg.Analyzer(NtupleProducer,
                      name = 'NtupleProducer',
                      outputfile = 'events.root',
                      treename = 'events',
                      event_content = event_content_test)

sequence = cfg.Sequence([
# Analyzers
    json,
    vertex,
# Muon
    muons,
    select_muon,
    exclude_muon,
    reweight_muon,
    one_muon,
    exclude_loose_muon,
# Electron
    electrons,
    select_electron,
    exclude_electron,
    reweight_electron,
    one_electron,
    exclude_loose_electron,
# Jets
    jets,
    jets_20_unclean,
    jet_20_electron_clean,
    jet_20_clean,
    jets_40,
    three_jets,
# b-Jets
    btagger,
    bjets_60,
    one_bjets,
# Rescaling
    trigger, 
    # trigger_match,
    # met_filters,
    lheweight,
    pileup, 
    njets_ana,
    region_ana,
# Mets
    pfmetana,
# Ntuple
    #debugger,
    ntuple
])


############################################################################
from PhysicsTools.Heppy.analyzers.core.EventSelector import EventSelector

if events_to_pick:
    from CMGTools.H2TauTau.htt_ntuple_base_cff import eventSelector
    eventSelector.toSelect = events_to_pick
    sequence.insert(0, eventSelector)

# the following is declared in case this cfg is used in input to the
# heppy.py script
from PhysicsTools.HeppyCore.framework.eventsfwlite import Events
config = cfg.Config(components=selectedComponents,
                    sequence=sequence,
                    services=[],
                    events_class=Events)

printComps(config.components, True)
