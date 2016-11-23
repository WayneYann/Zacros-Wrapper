# -*- coding: utf-8 -*-
"""
Created on Sun Mar 27 20:28:48 2016

@author: RDX
"""

import matplotlib.pyplot as plt
import matplotlib as mat
import numpy as np
import os, shutil
import copy

from mpi4py import MPI

from Replicates import Replicates
from KMC_Run import KMC_Run
from Helper import Helper

class RateRescaling:
    
    def __init__(self):
        
        self.summary_filename = 'rescaling_output.txt'
        self.scale_parent_fldr = ''
        self.batch = Replicates()
        self.SDF_mat = []        # scaledown factors for each iteration
        self.tfinalvec = []         # t_final for each iteration
        self.rxn_names = []
        
    def ReachSteadyStateAndRescale(self, Product, template_folder, exe, include_stiff_reduc = True, max_events = int(1e4), max_iterations = 15, stiff_cutoff = 1, ss_inc = 2.0, n_samples = 100, n_runs = 10):

        COMM = MPI.COMM_WORLD
        Helper.ClearFolderContents(self.scale_parent_fldr)

        # Placeholder variables
        prev_batch = Replicates()
        cum_batch = Replicates()
        
        # Convergence variables
        is_steady_state = False
        unstiff = False
        converged = unstiff and is_steady_state
        iteration = 1
        SDF_vec = []        # scaledown factors for each iteration
        scale_final_time = ss_inc

        while not converged and iteration <= max_iterations:
            
            # Make folder for iteration
            iter_fldr = self.scale_parent_fldr + 'Iteration_' + str(iteration) + '/'
            if COMM.rank == 0:
                if not os.path.exists(iter_fldr):
                    os.makedirs(iter_fldr)
                
            # Create object for batch
            cur_batch = Replicates()
            cur_batch.ParentFolder = iter_fldr
            cur_batch.n_runs = n_runs
            cur_batch.Product = Product
            
            cur_batch.runtemplate = KMC_Run()
            cur_batch.runtemplate.exe_file = exe
            cur_batch.runtemplate.Path = template_folder
            cur_batch.runtemplate.ReadAllInput()
            
            if iteration == 1:              # Event sampling
            
                # Set sampling parameters
                cur_batch.runtemplate.Conditions['MaxStep'] = max_events
                cur_batch.runtemplate.Conditions['SimTime']['Max'] = 'inf'
                cur_batch.runtemplate.Conditions['WallTime']['Max'] = 'inf'
                cur_batch.runtemplate.Conditions['restart'] = False
                
                cur_batch.runtemplate.Report['procstat'] = ['event', max_events / n_samples]
                cur_batch.runtemplate.Report['specnum'] = ['event', max_events / n_samples]
                cur_batch.runtemplate.Report['hist'] = ['event', max_events]       # only record the initial and final states

                SDF_vec = np.ones(cur_batch.runtemplate.Reactions['nrxns'])         # Initialize scaledown factors
            
            elif iteration > 1:             # Time sampling

                # Change sampling
                cur_batch.runtemplate.Conditions['MaxStep'] = 'inf'
                cur_batch.runtemplate.Conditions['WallTime']['Max'] = 'inf'
                cur_batch.runtemplate.Conditions['restart'] = False
                cur_batch.runtemplate.Conditions['SimTime']['Max'] = prev_batch.runList[0].Performance['t_final'] * scale_final_time
                cur_batch.runtemplate.Conditions['SimTime']['Max'] = float('{0:.3E} \t'.format(cur_batch.runtemplate.Conditions['SimTime']['Max']))     # round to 4 significant figures
                cur_batch.runtemplate.Report['procstat'] = ['time', cur_batch.runtemplate.Conditions['SimTime']['Max'] / n_samples]
                cur_batch.runtemplate.Report['specnum'] = ['time', cur_batch.runtemplate.Conditions['SimTime']['Max'] / n_samples]
                cur_batch.runtemplate.Report['hist'] = ['time', cur_batch.runtemplate.Conditions['SimTime']['Max']]
                
                if include_stiff_reduc:
                    cur_batch.runtemplate.AdjustPreExponentials(SDF_vec)
                
            cur_batch.BuildJobsFromTemplate()
                
            # Use continuation
            if iteration > 1:
                for run_ind in range(n_runs):
                    cur_batch.runList[run_ind].StateInput['Type'] = 'history'
                    cur_batch.runList[run_ind].StateInput['Struct'] = prev_batch.runList[run_ind].History[-1]
            
            # Run jobs and read output
            cur_batch.BuildJobFiles()
            cur_batch.RunAllJobs()
            cur_batch.ReadMultipleRuns()
            
            # Add data to running list
            COMM.Barrier()
            if iteration == 1:
                pass            # Do not use data from first run because it is on event rather than time
            elif iteration == 2:
                cum_batch = copy.deepcopy(cur_batch)
            elif iteration > 2:
                for run_ind in range(n_runs):
                    cum_batch.runList[run_ind] = KMC_Run.time_sandwich(cum_batch.runList[run_ind], cur_batch.runList[run_ind])
            
            # Test steady-state
            if iteration == 1:
                is_steady_state = False
            else:
                cum_batch.AverageRuns()
                cum_batch.runAvg.Path = iter_fldr
                correl = cum_batch.CheckAutocorrelation(Product)
                not_change = cum_batch.runAvg.CheckSteadyState(Product)
                is_steady_state = np.abs(correl) < 0.05 and not_change
                
                # Record information about the iteration
                cum_batch.runAvg.CalcRateTraj(Product)
        
                cum_batch.runAvg.PlotSurfSpecVsTime()        
                cum_batch.runAvg.PlotIntPropsVsTime()
                cum_batch.runAvg.PlotRateVsTime()  
            
            # Test stiffness
            cur_batch.AverageRuns()
            scaledown_data = self.ProcessStepFreqs(cur_batch.runAvg)         # compute change in scaledown factors based on simulation result
            delta_sdf = scaledown_data['delta_sdf']
            rxn_speeds = scaledown_data['rxn_speeds']
            if include_stiff_reduc:
                unstiff = np.max(np.abs(np.log10(delta_sdf))) < stiff_cutoff
            else:
                unstiff = True
    
            if COMM.rank == 0:
                # Record iteartion data in output file
                with open(iter_fldr + 'Iteration_summary.txt', 'w') as txt:   
                    txt.write('----- Iteration #' + str(iteration) + ' -----\n')
                    txt.write('t_final: {0:.3E} \n'.format(cur_batch.runAvg.Specnum['t'][-1]))
                    txt.write('stiff: ' + str(not unstiff) + '\n')
                    txt.write('steady-state: ' + str(is_steady_state) + '\n')
                    for rxn_name in cur_batch.runAvg.Reactions['names']:
                        txt.write(rxn_name + '\t')
                    txt.write('\n')
                    for sdf in delta_sdf:
                        txt.write('{0:.3E} \t'.format(sdf))
                    txt.write('\n')
                    for rxn_speed in rxn_speeds:
                        txt.write(rxn_speed + '\t')
            
            # Update scaledown factors
            for ind in range(len(SDF_vec)):
                SDF_vec[ind] = SDF_vec[ind] * delta_sdf[ind]
                
            scale_final_time = np.max( [1.0/np.min(delta_sdf), ss_inc] )
            
            prev_batch = copy.deepcopy(cur_batch)
            converged = unstiff and is_steady_state
            iteration += 1
    
    # Process KMC output and determine how to further scale down reactions
    def ProcessStepFreqs(self, run, stiff_cut = 100, equilib_cut = 0.05):
        
        delta_sdf = np.ones(run.Reactions['nrxns'])    # initialize the marginal scaledown factors
        rxn_speeds = []
        
        # data analysis
        freqs = run.Procstat['events'][-1,:]
        fwd_freqs = freqs[0::2]
        bwd_freqs = freqs[1::2]
        net_freqs = fwd_freqs - bwd_freqs
        tot_freqs = fwd_freqs + bwd_freqs
        
        fast_rxns = []
        slow_rxns = []        
        for i in range(len(tot_freqs)):
            if tot_freqs[i] == 0:
                slow_rxns.append(i)
                rxn_speeds.append('slow')
            else:
                PE = float(net_freqs[i]) / tot_freqs[i]
                if np.abs(PE) < equilib_cut:
                    fast_rxns.append(i)
                    rxn_speeds.append('fast')
                else:
                    slow_rxns.append(i)
                    rxn_speeds.append('slow')
        
        # Find slow scale rate
        slow_freqs = [1.0]      # put an extra 1 in case no slow reactions occur
        for i in slow_rxns:
            slow_freqs.append(tot_freqs[i])
        slow_scale = np.max(slow_freqs)
        
        # Adjust fast reactions closer to the slow scale
        for i in fast_rxns:
            delta_sdf[i] = np.min([1.0, stiff_cut * float(slow_scale) / tot_freqs[i]])
            
        return {'delta_sdf': delta_sdf, 'rxn_speeds': rxn_speeds}
    
    def PlotStiffnessReduction(self):
        
        # Data
        SDF_dims = self.SDF_mat.shape
        n_iterations = SDF_dims[0]
        n_rxns = SDF_dims[1]
        iterations = range(n_iterations)
        if self.rxn_names == []:
            self.rxn_names = self.batch.runtemplate.Reactions['names']
        
        
        # Plotting
        mat.rcParams['mathtext.default'] = 'regular'
        mat.rcParams['text.latex.unicode'] = 'False'
        mat.rcParams['legend.numpoints'] = 1
        mat.rcParams['lines.linewidth'] = 2
        mat.rcParams['lines.markersize'] = 16
        
        plt.figure()
        
        for i in range(n_rxns):
            plt.plot(iterations, np.transpose(self.SDF_mat[:,i]), 'o-', markersize = 15)
        
        plt.xticks(size=24)
        plt.yticks(size=24)
        plt.xlabel('iterations',size=30)
        plt.ylabel('scaledown factor',size=30)
        plt.legend(self.rxn_names, loc=1, prop={'size':20}, frameon=False)
        plt.show()
        
        plt.yscale('log')
        ax = plt.subplot(111)
        pos = [0.2, 0.15, 0.7, 0.8]
        ax.set_position(pos)
        
    def PlotFinalTimes(self):
        
        # Data
        SDF_dims = self.SDF_mat.shape
        n_iterations = SDF_dims[0]-1
        iterations = range(1,n_iterations+1)
        rxn_labels = []
        
        # Plotting
        mat.rcParams['mathtext.default'] = 'regular'
        mat.rcParams['text.latex.unicode'] = 'False'
        mat.rcParams['legend.numpoints'] = 1
        mat.rcParams['lines.linewidth'] = 2
        mat.rcParams['lines.markersize'] = 16
        
        plt.figure()
        
        plt.plot(iterations, self.tfinalvec, 'o-', markersize = 15)
        
        plt.xticks(size=24)
        plt.yticks(size=24)
        plt.xlabel('iterations',size=30)
        plt.ylabel('final KMC time (s)',size=30)
        plt.legend(rxn_labels,loc=1,prop={'size':20},frameon=False)
        plt.xlim([0,n_iterations])
        plt.show()
        
        plt.yscale('log')
        ax = plt.subplot(111)
        pos = [0.2, 0.15, 0.7, 0.8]
        ax.set_position(pos)
        
    def ReadSummaryFile(self):
        
        with open(self.scale_parent_fldr + self.summary_filename,'r') as txt:
            RawTxt = txt.readlines()
        
        lines_per_iter = 8
        n_iters =  (len(RawTxt) - 3) / lines_per_iter
        n_rxns = len(RawTxt[7].split())
        SDFcum = np.ones(n_rxns)
        
        self.SDF_mat    = np.zeros([n_iters+1, n_rxns])
        self.SDF_mat[0,:] = SDFcum
        self.rxn_names = RawTxt[6].split()
        
        for ind in range(n_iters):
            self.tfinalvec.append(float(RawTxt[ind * lines_per_iter + 3].split()[1]))
            sdf_line = RawTxt[ind * lines_per_iter + 7].split()
            
            for rxn_ind in range(n_rxns):
                SDFcum[rxn_ind] = SDFcum[rxn_ind] * float(sdf_line[rxn_ind])
            
            self.SDF_mat[ind+1,:] = SDFcum