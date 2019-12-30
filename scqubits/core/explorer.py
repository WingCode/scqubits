# explorer.py
#
# This file is part of scqubits.
#
#    Copyright (c) 2019, Jens Koch and Peter Groszkowski
#    All rights reserved.
#
#    This source code is licensed under the BSD-style license found in the
#    LICENSE file in the root directory of this source tree.
############################################################################

import matplotlib.pyplot as plt
import numpy as np

try:
    import ipywidgets
except ImportError:
    raise Exception("ImportError: failed to import ipywidgets. For use of scqubits.explorer,"
                    "ipywidgets must be installed")

import scqubits.utils.sweep_plotting as splot
from scqubits.settings import DEFAULT_ENERGY_UNITS


class Explorer:
    """
    This class allows interactive exploration of coupled quantum systems. The generate() method pre-calculates spectral
    data as a function of a given parameter, which can then be displayed and modified by sliders (when inside jupyter
    notebook or jupyter lab).

    Parameters
    ----------
    sweep: ParameterSweep
    evals_count: int
    figsize: tuple(int,int), optional
    """
    def __init__(self, sweep, evals_count, figsize=(10, 10)):
        self.param_name = sweep.param_name
        self.param_vals = sweep.param_vals
        self.param_count = sweep.param_count
        self.sweep = sweep
        self.evals_count = evals_count
        self.figsize = figsize

    def plot_explorer_panels(self, param_val, photonnumber, initial_index, final_index,
                             chi_qbt_index, chi_osc_index):
        def display_bare_spectrum(index):
            title = 'bare spectrum: subsystem {} ({})'.format(self.sweep.hilbertspace.index(subsys), subsys._sys_type)
            __ = splot.bare_spectrum(self.sweep, subsys, title=title, fig_ax=(fig, axes_list_flattened[index]))
            axes_list_flattened[index].axvline(param_val, color='gray', linestyle=':')

        def display_bare_wavefunctions(index):
            title = 'wavefunctions: subsystem {} ({})'.format(self.sweep.hilbertspace.index(subsys), subsys._sys_type)
            __ = splot.bare_wavefunction(self.sweep, param_val, subsys, title=title,
                                         fig_ax=(fig, axes_list_flattened[index]))

        def display_dressed_spectrum(index):
            title = r'{} $\rightarrow$ {}: {:.4f} {}'.format(bare_initial, bare_final, energy_difference,
                                                             DEFAULT_ENERGY_UNITS)
            __ = splot.dressed_spectrum(self.sweep, title=title, fig_ax=(fig, axes_list_flattened[index]))
            axes_list_flattened[index].axvline(param_val, color='gray', linestyle=':')
            axes_list_flattened[index].scatter([param_val] * 2, [energy_initial, energy_final], s=40, c='gray')

        def display_n_photon_qubit_transitions(index):
            title = r'{}-photon qubit transitions, {} $\rightarrow$'.format(photonnumber, bare_initial)
            __ = splot.n_photon_qubit_spectrum(self.sweep, photonnumber, self.sweep.hilbertspace.osc_subsys_list,
                                               initial_state_ind=initial_index, title=title,
                                               fig_ax=(fig, axes_list_flattened[index]))
            axes_list_flattened[index].axvline(param_val, color='gray', linestyle=':')
            axes_list_flattened[index].scatter([param_val], [(energy_final - energy_initial) / photonnumber], s=40,
                                               c='gray')

        def display_chi_01():
            __ = splot.chi_01(self.sweep, chi_qbt_index, chi_osc_index, param_index=param_index,
                              fig_ax=(fig, axes_list_flattened[index]))
            axes_list_flattened[index].axvline(param_val, color='gray', linestyle=':')

        if initial_index >= final_index:
            print("The initial-state index must be smaller than the final-state index, here.")
            return

        param_index = np.searchsorted(self.param_vals, param_val)
        param_val = self.param_vals[param_index]
        bare_initial = self.sweep.hilbertspace.get_bare_index(initial_index, param_index)
        bare_final = self.sweep.hilbertspace.get_bare_index(final_index, param_index)
        energy_ground = self.sweep.lookup_energy_dressed_index(0, param_index)
        energy_initial = self.sweep.lookup_energy_dressed_index(initial_index, param_index) - energy_ground
        energy_final = self.sweep.lookup_energy_dressed_index(final_index, param_index) - energy_ground
        energy_difference = energy_final - energy_initial

        dynamic_subsys_count = len(self.sweep.subsys_update_list)
        ncols = 2
        nrows = dynamic_subsys_count + 2
        fig, axs = plt.subplots(ncols=ncols, nrows=nrows, figsize=self.figsize)

        axes_list_flattened = [elem for sublist in axs for elem in sublist]
        index = 0
        # start with plots for bare subsystems that vary with the external parameter:
        # left: bare spectrum, right: wavefunctions
        for index, subsys in enumerate(self.sweep.subsys_update_list):
            display_bare_spectrum(index)
            index += 1
            display_bare_wavefunctions(index)
        index += 1

        # next row - left: dressed spectrum, right: n-photon qubit transition spectrum
        display_dressed_spectrum(index)
        index += 1
        display_n_photon_qubit_transitions(index)
        index += 1

        # next row: left - dispersive shifts
        display_chi_01()

        fig.tight_layout()
        return fig, axs

    def interact(self):
        param_min = self.param_vals[0]
        param_max = self.param_vals[-1]
        param_step = self.param_vals[1] - self.param_vals[0]

        qbt_indices = [index for (index, subsystem) in self.sweep.hilbertspace.qbt_subsys_list]
        osc_indices = [index for (index, subsystem) in self.sweep.hilbertspace.osc_subsys_list]

        param_slider = ipywidgets.FloatSlider(min=param_min, max=param_max, step=param_step,
                                              description=self.param_name, continuous_update=False)
        photon_slider = ipywidgets.IntSlider(value=1, min=1, max=4, description='photon number')
        initial_slider = ipywidgets.IntSlider(value=0, min=0, max=self.evals_count, description='initial state index')
        final_slider = ipywidgets.IntSlider(value=1, min=1, max=self.evals_count, description='final state index')
        chi_qbt_dropdown = ipywidgets.Dropdown(options=qbt_indices, description='qubit subsys')
        chi_osc_dropdown = ipywidgets.Dropdown(options=osc_indices, description='oscillator subsys')

        def update_min_final_index(*args):
            final_slider.min = initial_slider.value + 1

        initial_slider.observe(update_min_final_index, 'value')

        out = ipywidgets.interactive_output(self.plot_explorer_panels,
                                            {'param_val': param_slider,
                                             'photonnumber': photon_slider,
                                             'initial_index': initial_slider,
                                             'final_index': final_slider,
                                             'chi_qbt_index': chi_qbt_dropdown,
                                             'chi_osc_index': chi_osc_dropdown})

        left_box = ipywidgets.VBox([param_slider])
        mid_box = ipywidgets.VBox([initial_slider, final_slider, photon_slider])
        right_box = ipywidgets.VBox([chi_qbt_dropdown, chi_osc_dropdown])

        ui = ipywidgets.HBox([left_box, mid_box, right_box])
        display(ui, out)
