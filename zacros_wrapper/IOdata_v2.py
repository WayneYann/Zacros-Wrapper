# -*- coding: utf-8 -*-
'''
         -----------------------------------------------------
               Read all Zacros input and output files.
            Calculate cluster energies, pre-exponential
             factors and activation energeies using the
           DFT_to_Thermochemistry.py code.  Replace those
           values in the Zacros energetics_input.dat and
            mechanism_input.dat files and write the new
                         file versions.

                     Vlachos Research Group
                Chemical and Biomolecular Egineering
                      University of Delaware

                     Gerhard R Wittreich, P.E.
          -----------------------------------------------------

Created on Fri Apr 28 10:49:53 2017

@author: wittregr

Adopted from Matlab code written and modified by:

                        Marcel Nunez
                            and
                        Taylor Robie

 This program contains the class objects used to read energy, vibration and
 molecular configuration data and determine the standard entropy and enthalpy
 and heat capacities at various temperatures.

'''

import os as _os
import numpy as _np
import re as _re
import random as _random
import linecache as _linecache
import DFT_to_Thermochemistry as _thermo

from GRW_constants import constant as _c
from Helper import ReadWithoutBlankLines as _ReadWithoutBlankLines
from Helper import ReturnUnique as _ReturnUnique
from Helper import rawbigcount as _rawbigcount
reload(_thermo)


'''
 Class definitions for:

     Zacros input file      Class object
     -----------------      ------------
     energetics_input.dat   ClusterIn
     mechanism_input.dat    MechanismIn
     simulation_input.dat   SimIN
     lattice_input.dat      LatticeIn
     state_input.dat        StateIn

     Zacros output file    Class object
     ------------------    ------------
     general_output.txt    Performance
     history_output.txt    History
     procstat_output.txt   Procstat
     specnum_output.txt    Specnum
     clusterocc.bin        Binary
     Prop_output.bin       Binary
     SA_output.bin         Binary
'''


'''
============ Classes to handle input files ============
'''

class Cluster():

    def __init__(self):
    
        self.name = None
        self.variant_list = []
        self.sites = None
        self.neighboring = None
        self.latstate = None
        
    
class cluster_variant():

    def __init__(self):
    
        self.name = None
        self.site_types = None
        self.graph_multiplicity = 1
        self.cluster_eng = 0.0
    

class ClusterIn(object):

    '''
    Handles data from energetics_input.dat
    '''

    fname = 'energetics_input.dat'

    
    def __init__(self):
    
        self.cluster_list = []
        

    def FindCluster(self, Cluster_Num):     # FIX THIS METHOD
    
        '''
        Method finds the Cluster and Variant index of the nth
        Cluster-Variant where n is specified by Cluster_Num and
        the indices are returned as C.index (Cluster)
        and V.index (Variant) such that Cluster[C_index].variant_name[V_index]
        represents the name of the nth Cluster-Variant
        '''
        
        Cluster_Num = int(Cluster_Num)
        Tvariants = sum(s.nVariant for s in self.cluster_list)
        if Tvariants >= Cluster_Num and Cluster_Num >= 1:
            var = []
            for s in self.cluster_list:
                var.append(s.nVariant)
            var = _np.array(var)
            C_index = _np.argmin(var.cumsum() < Cluster_Num)
            V_index = Cluster_Num - sum(var[0:C_index]) - 1
        else:
            C_index = V_index = -1
        return(C_index, V_index)
        
        
    def ReadIn(self, fldr):
    
        '''
        Read energetics_input.dat
        '''
        
        RawTxt = _ReadWithoutBlankLines(_os.path.join(fldr, self.fname), CommentLines=False)
        nLines = len(RawTxt)
    
        nClusters = 0
        for i in range(0, nLines):
            if RawTxt[i].split()[0] == 'cluster':
                nClusters += 1
    
        ClusterInd = _np.array([ [0, 0] ] * nClusters)
        Count = 0
        for i in range(0, nLines):
            if RawTxt[i].split()[0] == 'cluster':
                ClusterInd[Count, 0] = i
            if RawTxt[i].split()[0] == 'end_cluster':
                ClusterInd[Count, 1] = i
                Count += 1
    
        nClusterTotal = 0
        self.cluster_list = [Cluster() for j in range(nClusters)]
        
        # Loop through all clusters
        for j in range(nClusters):
        
            self.cluster_list[j].name = RawTxt[ClusterInd[j, 0]].split()[1]
            n_variants = 0
            
            for i in range(ClusterInd[j, 0] + 1, ClusterInd[j, 1]):
                if RawTxt[i].split()[0] == 'variant':
                    n_variants += 1
                elif RawTxt[i].split()[0] == 'sites':
                    self.cluster_list[j].sites = int(RawTxt[i].split()[1])
                elif RawTxt[i].split()[0] == 'neighboring':
                    self.cluster_list[j].neighboring = RawTxt[i].split()[1:]
                elif RawTxt[i].split()[0] == 'lattice_state':
                    self.cluster_list[j].latstate = RawTxt[i + 1:i + 1 +
                                                    self.cluster_list[j].sites]
                    for k in range(0, len(self.cluster_list[j].latstate)):
                        self.cluster_list[j].latstate[k] =\
                        self.cluster_list[j].latstate[k].split('\n')[0]
    
            nClusterTotal += n_variants
            
            # Find beginning and ending lines for each variant
            variantInd = _np.array([[0, 0]]*n_variants)
            Count = 0
            for i in range(ClusterInd[j, 0]+1, ClusterInd[j, 1]):
                if RawTxt[i].split()[0] == 'variant':
                    variantInd[Count, 0] = i
                if RawTxt[i].split()[0] == 'end_variant':
                    variantInd[Count, 1] = i
                    Count += 1
                    
            self.cluster_list[j].variant_list = [cluster_variant() for k in range(n_variants)]

            # Loop through all variants for this cluster
            for k in range(n_variants):
            
                for i in range(variantInd[k, 0], variantInd[k, 1]):
                
                    if RawTxt[i].split()[0] == 'variant':
                        self.cluster_list[j].variant_list[k].name = RawTxt[i].split()[1]
                    elif RawTxt[i].split()[0] == 'site_types':
                        self.cluster_list[j].variant_list[k].site_types = RawTxt[i].split()[1:]
                    elif RawTxt[i].split()[0] == 'graph_multiplicity':
                        self.cluster_list[j].variant_list[k].graph_multiplicity = int(RawTxt[i].split()[1])
                    elif RawTxt[i].split()[0] == 'cluster_eng':
                        self.cluster_list[j].variant_list[k].cluster_eng = float(RawTxt[i].split()[1])
     
                        
    def WriteIn(self, fldr):
    
        '''
        Write energetics_input.dat
        '''
    
        with open(_os.path.join(fldr, self.fname), 'w') as txt:
        
            txt.write('energetics\n\n')
            
            for clustr in self.cluster_list:

                txt.write('#'*80 + '\n\n')
                txt.write('cluster ' + clustr.name + '\n\n')
                txt.write('  sites ' + str(clustr.sites) + '\n')
    
                if not clustr.neighboring is None:    # None when there is a point cluster
                    txt.write('  neighboring')
                    for j in range(0, len(clustr.neighboring)):
                        txt.write(' ' + clustr.neighboring[j])
                    txt.write('\n')
    
                txt.write('  lattice_state\n')
                for j in range(0, int(clustr.sites)):
                    txt.write(clustr.latstate[j] + '\n')
    
                txt.write('\n')
                
                for varnt in clustr.variant_list:
                
                    txt.write('  {} {}\n'.format('variant',
                            varnt.name ))
                    txt.write('    {:25}'.format('site_types'))
                    for k in range( len(varnt.site_types )):
                        txt.write('{} '.format
                                (varnt.site_types[k]))
                    txt.write('\n')
                    if int(varnt.graph_multiplicity ) > 0:
                        txt.write('    {:25}{}\n'.format('graph_multiplicity',
                                str(varnt.graph_multiplicity )))
                    txt.write('    {:25}{}\n'.format('cluster_eng',
                            str(varnt.cluster_eng)))
                    txt.write('  end_variant\n\n')
    
                txt.write('end_cluster\n\n')
                
            txt.write('#'*80 + '\n\n')
            txt.write('\n\nend_energetics')
            

class Reaction():

    def __init__(self):
    
        self.is_reversible = True
        self.gas_reacs_prods = None
        self.sites = None
        self.neighboring = None
        self.initial = None
        self.final = None
        self.variant_list = []

class rxn_variant():

    def __init__(self):
    
        self.name = None
        self.site_types = None              # site types
        self.pre_expon = None               # pre-exponential factor
        self.pe_ratio = None                # partial equilibrium ratio
        self.activ_eng = 0.0               # activation energy
        self.prox_factor = 0.5
        
        self.scaledown_factor = 1.0
        
            
class MechanismIn(object):

    '''
    Handles input from mechanism_input.dat
    '''
    
    fname = 'mechanism_input.dat'

    def __init__(self):
    
        self.rxn_list = []
        self.include_scaledown = False
        

    def FindReaction(self, Reaction_Num):       # FIX THIS METHOD
    
        '''
        Method finds the Reaction and Variant index of the nth
        Reaction-Variant where n is specified by Cluster_Num and
        the indices are returned as R.index (Reaction)
        and V.index (Variant) such that Reaction[R_index].variant_name[V_index]
        represents the name of the nth Reaction-Variant
        '''
        
        Reaction_Num = int(Reaction_Num)
        Tvariants = sum(s.nVariant for s in self.Reaction)
        if Tvariants >= Reaction_Num and Reaction_Num >= 1:
            var = []
            for s in self.Reaction:
                var.append(s.nVariant)
            var = _np.array(var)
            R_index = _np.argmin(var.cumsum() < Reaction_Num)
            V_index = Reaction_Num - sum(var[0:R_index]) - 1
        else:
            R_index = V_index = -1
        return(R_index, V_index)
        
        
    def ReadIn(self, fldr):
    
        '''
        Read mechanism_input.dat
        '''
        
        RawTxt = _ReadWithoutBlankLines(_os.path.join(fldr, self.fname), CommentLines=True)
        nLines = len(RawTxt)
        StiffCorrLine = -1
    
        self.rxn_list = []
        n_rxns = 0
        for i in range(nLines):
            if RawTxt[i].split()[0] == 'reversible_step':
                self.rxn_list.append( Reaction() )
                n_rxns += 1
            elif RawTxt[i].split()[0] == 'step':
                self.rxn_list.append( Reaction() )
                self.rxn_list[-1].is_reversible = False
                n_rxns += 1
            elif _re.search('# Automated stiffness reconditioning employed',
                            RawTxt[i]):
                StiffCorrLine = i
                self.include_scaledown = True
    
        if StiffCorrLine != -1:
            scaledown_factor_list = [_np.float(i) for i in RawTxt[StiffCorrLine+2].split(':')[1].split()]
    
        # Identify which lines of text are for each reaction
        MechInd = _np.array([[0, 0]]*n_rxns)
        Count = 0
        for i in range(nLines):
    
            if RawTxt[i].split()[0] == 'reversible_step' or RawTxt[i].split()[0] == 'step':
                MechInd[Count, 0] = i
    
            elif RawTxt[i].split()[0] == 'end_reversible_step':
                MechInd[Count, 1] = i
                Count += 1
    
            elif RawTxt[i].split()[0] == 'end_step':
                MechInd[Count, 1] = i
                Count += 1
        
        all_rxn_ind = 0     # Use this index to assign scaledown factors
        
        # Loop over list of recations
        for j in range(n_rxns):
    
            # Count the variants
    
            self.rxn_list[j].name = RawTxt[MechInd[j, 0]].split()[1]
            n_variants = 0
            InVariant = False
            StateLine = []
            for i in range(MechInd[j, 0] + 1, MechInd[j, 1]):
                if RawTxt[i].split()[0] == 'variant':
                    n_variants += 1
                    InVariant = True
                elif RawTxt[i].split()[0] == 'end_variant':
                    InVariant = False
                elif RawTxt[i].split()[0] == 'gas_reacs_prods':
                    self.rxn_list[j].gas_reacs_prods = RawTxt[i].split()[1:]
                elif RawTxt[i].split()[0] == 'sites':
                    nSites = int(RawTxt[i].split()[1])
                    self.rxn_list[j].sites = nSites
                elif RawTxt[i].split()[0] == 'neighboring':
                    self.rxn_list[j].neighboring = RawTxt[i].split()[1:]
                elif RawTxt[i].split()[0] == 'initial':
                    self.rxn_list[j].initial = []
                    LatState = RawTxt[i+1:i+1+nSites]
                    for k in range(0, len(LatState)):
                            self.rxn_list[j].initial.\
                            append(LatState[k].split('\n')[0])
                    for k in range(0, nSites):
                        StateLine.append(i+1+k)
                elif RawTxt[i].split()[0] == 'final':
                    self.rxn_list[j].final = []
                    LatState = RawTxt[i + 1:i + 1 + nSites]
                    for k in range(0, len(LatState)):
                            self.rxn_list[j].final.\
                            append(LatState[k].split('\n')[0])
                    for k in range(0, nSites):
                        StateLine.append(i+1+k)
                elif not InVariant and i not in StateLine:
                    print 'Unparsed line in mechanism input:'
                    print RawTxt[i]

            # Find beginning and ending lines for each variant
            variantInd = _np.array([[0, 0]]*n_variants)
            Count  = 0
            for i in range(MechInd[j, 0] + 1, MechInd[j, 1]):
                if RawTxt[i].split()[0] == 'variant':
                    variantInd[Count, 0] = i
                if RawTxt[i].split()[0] == 'end_variant':
                    variantInd[Count, 1] = i
                    Count += 1

            self.rxn_list[j].variant_list = [ rxn_variant() for i in range(n_variants) ]
                    
            # Loop over list of recation variants        
            for k in range( n_variants ):
            
                for i in range(variantInd[k, 0], variantInd[k, 1]):
                    if RawTxt[i].split()[0] == 'variant':
                        self.rxn_list[j].variant_list[k].name = RawTxt[i].split()[1]
                    elif RawTxt[i].split()[0] == 'site_types':
                        self.rxn_list[j].variant_list[k].site_types = RawTxt[i].split()[1:]
                    elif RawTxt[i].split()[0] == 'pre_expon':
                        self.rxn_list[j].variant_list[k].pre_expon = float(RawTxt[i].split()[1])
                    elif RawTxt[i].split()[0] == 'pe_ratio':
                        self.rxn_list[j].variant_list[k].pe_ratio = float(RawTxt[i].split()[1])
                    elif RawTxt[i].split()[0] == 'activ_eng':
                        self.rxn_list[j].variant_list[k].activ_eng = float(RawTxt[i].split()[1])
                    elif RawTxt[i].split()[0] == 'prox_factor':
                        self.rxn_list[j].variant_list[k].prox_factor = float(RawTxt[i].split()[1])
                    elif RawTxt[i].split()[0] == '#':
                        pass
                
                # Assign scaledown factor if it is present
                if StiffCorrLine != -1:
                    self.rxn_list[j].variant_list[k].scaledown_factor = scaledown_factor_list[all_rxn_ind]
                all_rxn_ind += 1


    def WriteIn(self, fldr):
    
        '''
        Write mechanism_input.dat
        '''

        with open(_os.path.join(fldr, self.fname), 'w') as txt:
        
            txt.write('mechanism\n\n')
            
            if self.include_scaledown:
                txt.write('# Automated stiffness reconditioning employed\n')
                txt.write('# \n')
                txt.write('# SDF: ')
                for i in self.scaledown_factors:
                    txt.write('{0:.5e} \t'.format(i))
                txt.write('\n\n')
            
            # Loop through reactions            
            for rxn in self.rxn_list :

                txt.write('#'*80 + '\n\n')

                if rxn.is_reversible:
                    txt.write('reversible_step ' + rxn.name + '\n')
                else:
                    txt.write('step ' + rxn.name + '\n')

                txt.write('  sites ' + str(rxn.sites) + '\n')
                if not rxn.neighboring is None:
                    txt.write('  neighboring')
                    for j in range(0, len(rxn.neighboring)):
                        txt.write(' ' + rxn.neighboring[j])
                    txt.write('\n')

                if not rxn.gas_reacs_prods is None:
                    txt.write('  {} {} {}\n'.format('gas_reacs_prods',
                              str(rxn.gas_reacs_prods[0]),
                              str(rxn.gas_reacs_prods[1])))

                txt.write('  initial\n')
                for j in range( rxn.sites ):
                    txt.write(rxn.initial[j] + '\n')

                txt.write('  final\n')
                for j in range( rxn.sites ):
                    txt.write(rxn.final[j] + '\n')

                txt.write('\n')
                
                # Loop through variants
                for rxn_var in  rxn.variant_list :
                    txt.write('  {} {}\n'.format('variant', rxn_var.name))
                    txt.write('    {:25}'.format('site_types'))
                    for k in range( len( rxn_var.site_types )):
                        txt.write('{} '.format( rxn_var.site_types[k]) )
                    txt.write('\n')
                    
                    # Write pre-exponential factor. Add comment if it has been rescaled
                    if rxn_var.scaledown_factor == 1.0:             # reaction has not been rescaled
                        txt.write('    {:25}{:.5e}\n'.format('pre_expon', rxn_var.pre_expon))
                    else:                                   # reaction has been rescaled
                        txt.write('    {:25}{:.5e}'.format('pre_expon', rxn_var.pre_expon))
                        txt.write( ('    # Pre-exponential has been ' + 'rescaled by a factor of {0:.5e}\n').format(rxn_var.scaledown_factor) )

                    if rxn.is_reversible:
                        txt.write('    {:25}{:.5e}\n'.format('pe_ratio', rxn_var.pe_ratio))
                        txt.write('    {:25}{:5.3f}\n'.format('prox_factor', (rxn_var.prox_factor) ) )
                        
                    txt.write('    {:25}{:4.2f}\n'.format('activ_eng', (rxn_var.activ_eng )) )
                        
                    txt.write('  end_variant\n\n')

                if rxn.is_reversible:
                    txt.write('end_reversible_step\n\n')
                else:
                    txt.write('end_step\n\n')

            txt.write('#'*80 + '\n\n')
            txt.write('\n\nend_mechanism')
        

class SimIn():

    '''
    Handles input from simulation_input.dat
    '''

    fname = 'simulation_input.dat'
    
    def __init__(self):
    
        self.TPD = False            # flag for temperature programmed desorption (TPD) mode
        self.TPD_start = None
        self.TPD_ramp = None
        self.T = None
        self.P = None
        
        self.gas_spec = []
        self.n_gas = 0
        self.gas_eng = []
        self.gas_MW = []
        self.gas_molfrac = []
        self.surf_spec = []
        self.surf_dent = []
        
        self.Seed = None
        self.restart = True
        self.WallTime_Max = ''

    def ReadIn(self, fldr):
    
        '''
        Read simulation_input.dat
        '''
        
        with open(_os.path.join(fldr, self.fname), 'r') as txt:
            RawTxt = txt.readlines()

        for i in RawTxt:
            if len(i.split()) > 0:
                if i[0] != '#':
                    i = i.split('#')[0]  # Don't parse comments
                    if i.split()[0] == 'temperature':
                        if i.split()[1] == 'ramp':
                            self.TPD = True
                            self.TPD_start = _np.float(i.split()[2])
                            self.TPD_ramp = _np.float(i.split()[3])
                        else:
                            self.T = _np.float(i.split()[1])
                    elif i.split()[0] == 'pressure':
                        self.P = _np.float(i.split()[1])
                    elif i.split()[0] == 'random_seed':
                        self.Seed = _np.int(i.split()[1])
                    elif i.split()[0] == 'no_restart':
                        self.restart = False
                    elif i.split()[0] == 'gas_specs_names':
                        self.gas_spec = i.split()[1:]
                        self.n_gas = len(self.gas_spec)
                    elif i.split()[0] == 'gas_energies':
                        for j in i.split()[1:]:
                            self.gas_eng.append(_np.float(j))
                    elif i.split()[0] == 'gas_molec_weights':
                        for j in i.split()[1:]:
                            self.gas_MW.append(_np.float(j))
                    elif i.split()[0] == 'gas_molar_fracs':
                        for j in i.split()[1:]:
                            self.gas_molfrac.append(_np.float(j))
                    elif i.split()[0] == 'surf_specs_names':
                        self.surf_spec = i.split()[1:]
                        self.n_surf = len(self.surf_spec)
                    elif i.split()[0] == 'surf_specs_dent':
                        for j in i.split()[1:]:
                            self.surf_dent.append(_np.int(j))
                    elif i.split()[0] == 'event_report':
                        self.event = i.split()[1]
                    elif i.split()[0] == 'snapshots':
                        self.hist = StateInc(i)
                    elif i.split()[0] == 'process_statistics':
                        self.procstat = StateInc(i)
                    elif i.split()[0] == 'species_numbers':
                        self.specnum = StateInc(i)
                    elif i.split()[0] == 'max_time':
                        if i.split()[1] == 'infinity':
                            self.SimTime_Max = 'inf'
                        else:
                            self.SimTime_Max =\
                             _np.float(i.split()[1])
                    elif i.split()[0] == 'max_steps':
                        if i.split()[1] == 'infinity':
                            self.MaxStep = 'inf'
                        else:
                            self.MaxStep = int(i.split()[1])
                    elif i.split()[0] == 'wall_time':
                        self.WallTime_Max = _np.int(i.split()[1])
                    elif i.split()[0] == 'finish' or\
                                         i.split()[0] == 'n_gas_species' or\
                                         i.split()[0] == 'n_surf_species':
                        pass
                        

    def WriteIn(self, fldr):
    
        '''
        Write simulation_input.dat
        '''

        with open(_os.path.join(fldr, self.fname), 'w') as txt:
            SeedTxt = ''
            if self.Seed is None:
                _random.seed()
                self.Seed = _random.randint(10000, 99999)
                SeedTxt = '# Random seed from Python wrapper'

            txt.write('#KMC simulation specification\n\n')
            txt.write('{:20}{:15}{}\n\n'.format('random_seed',
                      str(self.Seed), SeedTxt))
            
            # Write out temperature, which depends on TPD or constant temperature mode
            if self.TPD:
                txt.write('{:20}{:5.1f}{:5.1f}\n'.format('temperature\t ramp', self.TPD_start, self.TPD_ramp))
            else:
                txt.write('{:20}{:5.1f}\n'.format('temperature', self.T))
                
            txt.write('{:20}{:5.1f}\n\n'.format('pressure',
                      self.P))
            txt.write('{:20}{}\n'.format('n_gas_species',
                      str(self.n_gas)))
            txt.write('{:20}'.format('gas_specs_names'))
            for i in range(0, self.n_gas):
                txt.write('{:15}'.format(self.gas_spec[i]))

            GasList = ['gas_energies', 'gas_molec_weights', 'gas_molar_fracs']
            GasList2 = ['gas_eng', 'gas_MW', 'gas_molfrac']
            for j in range(0, len(GasList)):
                txt.write('\n{:20}'.format(GasList[j]))
                for i in range(0, self.n_gas):
                    txt.write('{:15}'.format(str(getattr(self,
                              GasList2[j])[i])))

            txt.write('\n\n{:20}{}\n'.format('n_surf_species',
                      str(self.n_surf)))
            txt.write('{:20}'.format('surf_specs_names'))
            for i in range(0, self.n_surf):
                txt.write('{:15}'.format(self.surf_spec[i]))
            txt.write('\n{:20}'.format('surf_specs_dent'))

            for i in range(0, self.n_surf):
                txt.write('{:15}'.format(str(self.surf_dent[i])))
            txt.write('\n\n')

            if self.hist[0] == 'off':
                txt.write('{:20}{}\n'.format('snapshots', 'off'))
            elif self.hist[0] == 'event':
                txt.write('{:20}{} {} {}\n'.format('snapshots', 'on',
                          self.hist[0],
                          str(int(self.hist[1]))))
            elif self.hist[0] == 'time':
                txt.write('{:20}{} {} {}\n'.format('snapshots', 'on',
                          self.hist[0],
                          str(_np.float(self.hist[1]))))
            if self.procstat[0] == 'off':
                txt.write('process_statistics  off\n')
            elif self.procstat[0] == 'event':
                txt.write('{:20}{} {} {}\n'.format('process_statistics', 'on',
                          self.procstat[0],
                          str(int(self.procstat[1]))))
            elif self.procstat[0] == 'time':
                txt.write('{:20}{} {} {}\n'.format('process_statistics', 'on',
                          self.procstat[0],
                          str(_np.float(self.procstat[1]))))

            if self.specnum[0] == 'off':
                txt.write('species_numbers     off\n')
            elif self.specnum[0] == 'event':
                txt.write('{:20}{} {} {}\n'.format('species_numbers', 'on',
                          self.specnum[0],
                          str(int(self.specnum[1]))))
            elif self.specnum[0] == 'time':
                txt.write('{:20}{} {} {}\n'.format('species_numbers', 'on',
                          self.specnum[0],
                          str(_np.float(self.specnum[1]))))
            txt.write('{:20}{}\n\n'.format('event_report',
                      self.event))

            if self.MaxStep == '' or\
               _re.search('inf', str(self.MaxStep)):
                txt.write('{:20}{}\n'.format('max_steps', 'infinity'))
            else:
                txt.write('{:20}{}\n'.format('max_steps',
                          str(self.MaxStep)))

            if self.SimTime_Max == '' or\
               _re.search('inf', str(self.SimTime_Max)):
                txt.write('{:20}{}\n'.format('max_time', 'infinity\n'))
            else:
                txt.write('{:20}{}\n'.format('max_time',
                          str(self.SimTime_Max)))
            if self.WallTime_Max == '' or\
               _re.search('inf', str(self.WallTime_Max)):
                txt.write('\n')
            else:
                txt.write('\n{:20}{}\n\n'.format('wall_time',
                          str(self.WallTime_Max)))

            if not self.restart:
                txt.write('no_restart\n')
            txt.write('finish\n')


class StateIn(object):

    '''
    Handles input from state_input.dat
    '''
    
    fname = 'state_input.dat'

    def __init__(self):
    
        self.Type = None    # None: No state_input.dat, StateInput: has read state_input.dat, history: read from history file previously
        self.Struct = None
        
    def ReadIn(self, fldr):
    
        '''
        Read state_input.dat
        '''

        if _os.path.isfile(_os.path.join(fldr, 'state_input.dat')):
        
            with open(_os.path.join(fldr, 'state_input.dat'), 'r') as Txt:
                RawTxt = Txt.readlines()
                
            self.Struct = []
            for i in RawTxt:
                self.Struct.append(i.split('\n')[0])
                
            self.Type = 'StateInput'
            
        else:
            self.Type = None
        

    def WriteIn(self, fldr):
    
        '''
        Write state_input.dat
        '''

        if self.Type is None:
            pass

        elif self.Type == 'StateInput':
            with open(_os.path.join(fldr, self.fname), 'w') as txt:
                for i in self.Struct:
                    txt.write(i + '\n')

        elif self.Type == 'history':

            Lattice = self.Struct
            UniqSpec = _np.unique(Lattice[_np.not_equal(
                    Lattice[:, 2], 0), 1])
            nAds = len(UniqSpec)
            SpecIden = [0] * nAds
            AdsInfo = [[] for i in range(0, nAds)]
            DentInfo = [[] for i in range(0, nAds)]
            for i in range(0, nAds):
                for j in range(0, Lattice.shape[0]):
                    if UniqSpec[i] == Lattice[j, 1]:
                        AdsInfo[i].append(j + 1)
                        DentInfo[i].append(Lattice[j, 3])
                        SpecIden[i] = Lattice[j, 2]

            if nAds > 0:
                with open(_os.path.join(fldr, self.fname), 'w') as txt:
                    txt.write('initial_state\n')
                    for i in range(0, nAds):
                        txt.write('  seed_on_sites  {:10}'.
                                  format(self.surf_spec
                                         [SpecIden[i]-1], 10))
                        for j in range(0, len(DentInfo[i])):
                            for k in range(0, len(DentInfo[i])):
                                if j + 1 == DentInfo[i][k]:
                                    txt.write(str(AdsInfo[i][k]) + '  ')
                        txt.write('\n')
                    txt.write('end_initial_state\n')
        else:
            print 'Unrecognized state_input type'
            print 'state_input not written'


'''
============ Classes to handle output files ============
'''
            
class PerformanceOut(object):

    '''
    Handles data from general_output.txt
    '''
    
    fname = 'general_output.txt'

    def __init__(self):
        pass
    
    def ReadGeneral(self, fldr):
        '''
        Read general_output.txt
        '''
        with open(_os.path.join(fldr, self.fname), 'r') as txt:
            RawTxt = txt.readlines()
    
        self.Performance = PerformanceIn()
        for i in range(0, len(RawTxt)):
            if _re.search('Number of elementary steps:', RawTxt[i]):
                nRxn = _np.int(RawTxt[i].split(':')[1])
            elif _re.search('Current KMC time:', RawTxt[i]):
                self.Performance.t_final = _np.float(RawTxt[i].split(':')[1])
            elif _re.search('Events occurred:', RawTxt[i]):
                self.Performance.events_occurred =\
                _np.float(RawTxt[i].split(':')[1])
            elif _re.search('Elapsed CPU time:', RawTxt[i]):
                after_colon = RawTxt[i].split(':')[1]
                self.Performance.CPU_time =\
                    _np.float(after_colon.split(' ')[-2])
            elif _re.search('Reaction network:', RawTxt[i]):
                RxnStartLine = i + 2
    
        if RawTxt[RxnStartLine].split()[0] == '1.':
            NameInd = 1
        else:
            NameInd = 0
    
        RxnNameList = []
        nuList = []
        for i in range(RxnStartLine, RxnStartLine + nRxn):
            RxnName = RawTxt[i].split()[NameInd][:-1]
            RxnNameList.append(RxnName)
            RxnStr = RawTxt[i][_re.search('Reaction:', RawTxt[i]).end():]
            RxnStrList = RxnStr.split()
            nu = [0] * (self.n_surf + self.n_gas)
            for j in range(0, len(RxnStrList)):
                if RxnStrList[j] == '->':
                    ArrowInd = j
            for j in range(0, len(RxnStrList)):
                if j < ArrowInd:
                    Sign = -1
                else:
                    Sign = 1
    
                if _re.search('\(', RxnStrList[j]):
                    SurfIden = _re.sub(r'\([^)]*\)', '', RxnStrList[j])
                    if SurfIden != '*':
                        SurfInd = [k for k in
                                range(0, len(self.surf_spec))
                                if SurfIden ==
                                self.surf_spec[k]][0]
                        nu[SurfInd] += Sign
                elif RxnStrList[j] != '->' and RxnStrList[j] != '+':
                    GasInd = [k for k in
                            range(0, len(self.gas_spec))
                            if RxnStrList[j] ==
                            self.gas_spec[k]][0]
                    nu[self.n_surf + GasInd] += Sign
            nuList.append(nu)
    
        self.Performance.Nu = nuList
        self.Performance.UniqNu = _ReturnUnique(nuList).tolist()


class ProcstatOut(object):
    
    '''
    Handles data from procstat_output.txt
    '''
    
    fname = 'procstat_output.txt'

    def __init__(self):
    
        self.Spacing = None
        self.t = None
        self.events = None
    
    def ReadProcstat(self, fldr):
        '''
        Read procstat_output.txt
        '''
        MaxLen = _np.int(2e4)
        with open(_os.path.join(fldr, self.fname), 'r') as txt:
            RawTxt = txt.readlines()

        if len(RawTxt) - 1 > MaxLen * 3:  # Procstat uses 3 lines per outputs
            Spacing = _np.int(_np.floor((len(RawTxt) - 1)/(MaxLen*3)))
            RawTxt2 = []
            for i in range(0, MaxLen):
                RawTxt2.append(RawTxt[i*Spacing*3+1])
                RawTxt2.append(RawTxt[i*Spacing*3+2])
                RawTxt2.append(RawTxt[i*Spacing*3+3])
        else:
            Spacing = 1
            RawTxt2 = RawTxt[1:]

        t = []
        events = []
        for i in range(0, len(RawTxt2)/3):
            t.append(_np.float(RawTxt2[i*3].split()[3]))
            eventsTemp = RawTxt2[i*3+2].split()[1:]
            for j in range(0, len(eventsTemp)):
                eventsTemp[j] = _np.int(eventsTemp[j])
            events.append(eventsTemp)

        self.Spacing = Spacing
        self.t = _np.asarray(t)
        self.events = _np.asarray(events)


class SpecnumOut(object):
    
    '''
    Handles data from specnum_output.txt
    '''
    
    fname = 'specnum_output.txt'
    
    def __init__(self):
        
        '''
        Initializes class variables
        '''
    
        self.Spacing = None
        self.nEvents = None
        self.t = None
        self.T = None
        self.E = None
        self.spec = None
        
    
    def ReadSpecnum(self, fldr):
        '''
        Read specnum_output.txt
        '''
        MaxLen = _np.int(2e4)
        with open(_os.path.join(fldr, self.fname), 'r') as txt:
            RawTxt = txt.readlines()

        if len(RawTxt) - 1 > MaxLen:
            Spacing = _np.int(_np.floor((len(RawTxt)-1)/MaxLen))
            RawTxt2 = []
            for i in range(0, MaxLen):
                RawTxt2.append(RawTxt[i*Spacing+1])
        else:
            Spacing = 1
            RawTxt2 = RawTxt[1:]

        nEvents = []
        t = []
        T = []
        E = []
        spec = []

        for i in range(0, len(RawTxt2)):
            LineSplit = RawTxt2[i].split()
            nEvents.append(_np.int(LineSplit[1]))
            t.append(_np.float(LineSplit[2]))
            T.append(_np.float(LineSplit[3]))
            E.append(_np.float(LineSplit[4]))
            specTemp = LineSplit[5:]
            for j in range(0, len(specTemp)):
                specTemp[j] = _np.int(specTemp[j])
            spec.append(specTemp)
            
        # Store data in class variables
        self.Spacing = Spacing
        self.nEvents = _np.asarray(nEvents)
        self.t = _np.asarray(t)
        self.T = _np.asarray(T)
        self.E = _np.asarray(E)
        self.spec = _np.asarray(spec)
    

class HistoryOut():

    '''
    Handles data from history_output.txt
    '''

    fname = 'history_output.txt'
    
    def __init__(self):
    
        n_snapshots = 0
        snapshots = None
        snap_times = None
        
    def ReadHistory(self, fldr, nSites):
    
        '''
        Read history_output.txt
        fldr: name of the folder containting the file
        nSites: number of lattice sites, obtained from lattice_output.txt
        '''
        
        HistPath = _os.path.join(fldr, self.fname)
        
        # Check if file exists
        if not _os.path.isfile(HistPath):
            return

        nLines = _rawbigcount(HistPath)
        
        self.n_snapshots = (nLines-6)/(nSites+2)
        self.snapshots = []
        self.snap_times = []

        for snap_ind in range(self.n_snapshots):
            snap_data = _np.array([[0]*4]*nSites)
            _linecache.clearcache()
            snap_header = _linecache.getline(HistPath, 8 + snap_ind *
                                             (nSites+2)-1).split()
            self.snap_times.append(snap_header[3])
            for i in range(0, nSites):
                snap_data[i, :] = _linecache.getline(HistPath, 8 + snap_ind *
                                                     (nSites+2)+i).split()
            self.snapshots.append(snap_data)
        

def StateInc(i):
    if _re.search('off', i):
        state = 'off'
        inc = ''
    elif _re.search('on time', i):
        state = 'time'
        inc = _np.float(i.split()[3])
    elif _re.search('on event', i):
        state = 'event'
        inc = _np.int(i.split()[3])
    return (state, inc)