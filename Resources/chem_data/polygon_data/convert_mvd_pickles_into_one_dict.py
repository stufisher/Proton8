import sys, os
from scitbx.array_family import flex
from libtbx import easy_pickle
from libtbx.str_utils import format_value

def fmt(value, format="%s"):
  return format_value(format, value).strip().lower()

def run():
  path = '/net/cci-filer1/vol1/share/pdbmtz/tmp/pickles/'
  files = os.listdir(path)
  fs = flex.std_string
  result = {
    "pdb_code": fs(),
    "space_group": fs(),
    "unit_cell": fs(),
    "unit_cell_volume": fs(),

    "anomalous_flag": fs(),
    "completeness_6A_inf": fs(),
    "completeness_d_min_inf": fs(),
    "completeness_in_range": fs(),
    "high_resolution": fs(),
    "low_resolution": fs(),
    "number_of_Fobs_outliers": fs(),
    "number_of_reflections": fs(),
    "test_set_size": fs(),
    "twinned": fs(),
    "wilson_b": fs(),

    "n_refl_cutoffs": fs(),
    "r_free_cutoffs": fs(),
    "r_work_cutoffs": fs(),

    "overall_scale_b_cart": fs(),
    "b_sol": fs(),
    "k_sol": fs(),
    "r_free": fs(),
    "r_work": fs(),
    "solvent_content_via_mask": fs(),

    "pdb_header_high_resolution": fs(),
    "pdb_header_low_resolution": fs(),
    "pdb_header_matthews_coeff": fs(),
    "pdb_header_program_name": fs(),
    "pdb_header_r_free": fs(),
    "pdb_header_r_work": fs(),
    "pdb_header_sigma_cutoff": fs(),
    "pdb_header_solvent_cont": fs(),
    "pdb_header_tls": fs(),
    "pdb_header_year": fs(),

    "number_of_mFo-DFc_peaks-3sigma": fs(),
    "number_of_mFo-DFc_peaks-6sigma": fs(),
    "number_of_mFo-DFc_peaks-9sigma": fs(),
    "number_of_mFo-DFc_peaks+3sigma": fs(),
    "number_of_mFo-DFc_peaks+6sigma": fs(),
    "number_of_mFo-DFc_peaks+9sigma": fs(),

    "number_of_residues_with_altlocs": fs(),
    "resname_classes": fs(),
    "rmsd_adp_iso_or_adp_equiv_bonded": fs(),

    "c_beta_deviations": fs(),
    "clashscore": fs(),
    "rama_allowed": fs(),
    "rama_favored": fs(),
    "rama_outliers": fs(),
    "rotamer_outliers": fs(),

    "dihedral_max_deviation": fs(),
    "dihedral_rmsd": fs(),
    "angle_max_deviation": fs(),
    "angle_rmsd": fs(),
    "chirality_max_deviation": fs(),
    "chirality_rmsd": fs(),
    "planarity_max_deviation": fs(),
    "planarity_rmsd": fs(),
    "bond_max_deviation": fs(),
    "bond_rmsd": fs(),
    "non_bonded_min_distance": fs(),

    "atom_types_and_count_str": fs(),
    "number_of_anisotropic": fs(),
    "number_of_atoms": fs(),
    "number_of_npd": fs(),
    "occupancy_max": fs(),
    "occupancy_mean": fs(),
    "occupancy_min": fs(),

    "adp_max_all": fs(),
    "adp_mean_all": fs(),
    "adp_min_all": fs(),

    "adp_max_sidechain": fs(),
    "adp_mean_sidechain": fs(),
    "adp_min_sidechain": fs(),

    "adp_max_backbone": fs(),
    "adp_mean_backbone": fs(),
    "adp_min_backbone": fs(),

    "adp_max_solvent": fs(),
    "adp_mean_solvent": fs(),
    "adp_min_solvent": fs()
  }

  for i_seq, file in enumerate(files):
    result_ = {}
    if(file.endswith(".pickle")):
      pdb_code = file[3:7]
      file = path+file
      print i_seq, pdb_code
      mvd = easy_pickle.load(file)
      if(len(mvd.models)>1): continue
      #print dir(mvd.crystal)
      result.setdefault("pdb_code"        ).append(fmt(value=pdb_code                        ))
      result.setdefault("space_group"     ).append(fmt(value=mvd.crystal.sg                  ))
      result.setdefault("unit_cell"       ).append(fmt(value=mvd.crystal.uc                  ))
      result.setdefault("unit_cell_volume").append(fmt(value=mvd.crystal.uc_vol,format="%.2f"))
      #print dir(mvd.data)
      result.setdefault("anomalous_flag"         ).append(fmt(value=mvd.data.anomalous_flag                       ))
      result.setdefault("completeness_6A_inf"    ).append(fmt(value=mvd.data.completeness_6A_inf   ,format="%.3f" ))
      result.setdefault("completeness_d_min_inf" ).append(fmt(value=mvd.data.completeness_d_min_inf,format="%.3f" ))
      result.setdefault("completeness_in_range"  ).append(fmt(value=mvd.data.completeness_in_range ,format="%.3f" ))
      result.setdefault("high_resolution"        ).append(fmt(value=mvd.data.high_resolution       ,format="%6.2f"))
      result.setdefault("low_resolution"         ).append(fmt(value=mvd.data.low_resolution        ,format="%6.2f"))
      result.setdefault("number_of_Fobs_outliers").append(fmt(value=mvd.data.number_of_Fobs_outliers              ))
      result.setdefault("number_of_reflections"  ).append(fmt(value=mvd.data.number_of_reflections                ))
      result.setdefault("test_set_size"          ).append(fmt(value=mvd.data.test_set_size                        ))
      result.setdefault("twinned"                ).append(fmt(value=mvd.data.twinned                              ))
      result.setdefault("wilson_b"               ).append(fmt(value=mvd.data.wilson_b,format="%7.2f"              ))
      #print dir(mvd.misc)
      result.setdefault("n_refl_cutoffs").append(fmt(value=mvd.misc.n_refl_cutoff               ))
      result.setdefault("r_free_cutoffs").append(fmt(value=mvd.misc.r_free_cutoff,format="%7.4f"))
      result.setdefault("r_work_cutoffs").append(fmt(value=mvd.misc.r_work_cutoff,format="%7.4f"))
      #print dir(mvd.model_vs_data)
      result.setdefault("overall_scale_b_cart"    ).append(fmt(value=" ".join(["%.2f"%i for i in mvd.model_vs_data.b_cart])   ))
      result.setdefault("b_sol"                   ).append(fmt(value=mvd.model_vs_data.b_sol,                   format="%6.2f"))
      result.setdefault("k_sol"                   ).append(fmt(value=mvd.model_vs_data.k_sol,                   format="%5.2f"))
      result.setdefault("r_free"                  ).append(fmt(value=mvd.model_vs_data.r_free,                  format="%7.4f"))
      result.setdefault("r_work"                  ).append(fmt(value=mvd.model_vs_data.r_work,                  format="%7.4f"))
      result.setdefault("solvent_content_via_mask").append(fmt(value=mvd.model_vs_data.solvent_content_via_mask,format="%4.2f"))
      #print dir(mvd.pdb_header)
      result.setdefault("pdb_header_high_resolution").append(fmt(value=mvd.pdb_header.high_resolution))
      result.setdefault("pdb_header_low_resolution" ).append(fmt(value=mvd.pdb_header.low_resolution ))
      result.setdefault("pdb_header_matthews_coeff" ).append(fmt(value=mvd.pdb_header.matthews_coeff ))
      result.setdefault("pdb_header_program_name"   ).append(fmt(value=mvd.pdb_header.program_name   ))
      result.setdefault("pdb_header_r_free"         ).append(fmt(value=mvd.pdb_header.r_free         ))
      result.setdefault("pdb_header_r_work"         ).append(fmt(value=mvd.pdb_header.r_work         ))
      result.setdefault("pdb_header_sigma_cutoff"   ).append(fmt(value=mvd.pdb_header.sigma_cutoff   ))
      result.setdefault("pdb_header_solvent_cont"   ).append(fmt(value=mvd.pdb_header.solvent_cont   ))
      result.setdefault("pdb_header_tls"            ).append(fmt(value="%s (n_groups: %s)"%(str(mvd.pdb_header.tls.pdb_inp_tls.tls_present),str(len(mvd.pdb_header.tls.tls_selections)))))
      result.setdefault("pdb_header_year"           ).append(fmt(value=mvd.pdb_header.high_resolution))
      #print dir(mvd.maps)
      result.setdefault("number_of_mFo-DFc_peaks-3sigma").append(fmt(value=mvd.maps.peaks_minus_3))
      result.setdefault("number_of_mFo-DFc_peaks-6sigma").append(fmt(value=mvd.maps.peaks_minus_6))
      result.setdefault("number_of_mFo-DFc_peaks-9sigma").append(fmt(value=mvd.maps.peaks_minus_9))
      result.setdefault("number_of_mFo-DFc_peaks+3sigma").append(fmt(value=mvd.maps.peaks_plus_3 ))
      result.setdefault("number_of_mFo-DFc_peaks+6sigma").append(fmt(value=mvd.maps.peaks_plus_6 ))
      result.setdefault("number_of_mFo-DFc_peaks+9sigma").append(fmt(value=mvd.maps.peaks_plus_9 ))
      #print dir(mvd.models[0])
      result.setdefault("number_of_residues_with_altlocs" ).append(fmt(value=mvd.models[0].n_residues_in_altlocs)                     )
      result.setdefault("resname_classes"                 ).append(fmt(value=",".join(mvd.models[0].resname_classes))                 )
      result.setdefault("rmsd_adp_iso_or_adp_equiv_bonded").append(fmt(value=mvd.models[0].rms_b_iso_or_b_equiv_bonded,format="%6.2f"))
      #print dir(mvd.models[0].molprobity)
      if(mvd.models[0].molprobity is not None):
        result.setdefault("c_beta_deviations").append(fmt(mvd.models[0].molprobity.cbetadev)                                      )
        result.setdefault("clashscore"       ).append(fmt(value=mvd.models[0].molprobity.clashscore,format="%.2f")                )
        result.setdefault("rama_allowed"     ).append(fmt(value=mvd.models[0].molprobity.ramalyze_allowed[1]*100. ,format="%6.2f"))
        result.setdefault("rama_favored"     ).append(fmt(value=mvd.models[0].molprobity.ramalyze_favored[1]*100. ,format="%6.2f"))
        result.setdefault("rama_outliers"    ).append(fmt(value=mvd.models[0].molprobity.ramalyze_outliers[1]*100.,format="%6.2f"))
        result.setdefault("rotamer_outliers" ).append(fmt(value=mvd.models[0].molprobity.rotalyze[1]*100.         ,format="%6.2f"))
      else:
        result.setdefault("c_beta_deviations").append(fmt(None))
        result.setdefault("clashscore"       ).append(fmt(None))
        result.setdefault("rama_allowed"     ).append(fmt(None))
        result.setdefault("rama_favored"     ).append(fmt(None))
        result.setdefault("rama_outliers"    ).append(fmt(None))
        result.setdefault("rotamer_outliers" ).append(fmt(None))
      #print dir(mvd.models[0].geometry_all)
      result.setdefault("dihedral_max_deviation" ).append(fmt(value=mvd.models[0].geometry_all.d_max ,format="%8.3f"))
      result.setdefault("dihedral_rmsd"          ).append(fmt(value=mvd.models[0].geometry_all.d_mean,format="%8.3f"))
      result.setdefault("angle_max_deviation"    ).append(fmt(value=mvd.models[0].geometry_all.a_max ,format="%8.3f"))
      result.setdefault("angle_rmsd"             ).append(fmt(value=mvd.models[0].geometry_all.a_mean,format="%8.3f"))
      result.setdefault("chirality_max_deviation").append(fmt(value=mvd.models[0].geometry_all.c_max ,format="%8.3f"))
      result.setdefault("chirality_rmsd"         ).append(fmt(value=mvd.models[0].geometry_all.c_mean,format="%8.3f"))
      result.setdefault("planarity_max_deviation").append(fmt(value=mvd.models[0].geometry_all.p_max ,format="%8.3f"))
      result.setdefault("planarity_rmsd"         ).append(fmt(value=mvd.models[0].geometry_all.p_mean,format="%8.3f"))
      result.setdefault("bond_max_deviation"     ).append(fmt(value=mvd.models[0].geometry_all.b_max ,format="%8.3f"))
      result.setdefault("bond_rmsd"              ).append(fmt(value=mvd.models[0].geometry_all.b_mean,format="%8.3f"))
      result.setdefault("non_bonded_min_distance").append(fmt(value=mvd.models[0].geometry_all.n_min ,format="%8.3f"))
      #print dir(mvd.models[0].xray_structure_stat)
      result.setdefault("atom_types_and_count_str").append(fmt(value=mvd.models[0].xray_structure_stat.all.atom_counts_str))
      result.setdefault("number_of_anisotropic"   ).append(fmt(value=mvd.models[0].xray_structure_stat.all.n_aniso))
      result.setdefault("number_of_atoms"         ).append(fmt(value=mvd.models[0].xray_structure_stat.all.n_atoms))
      result.setdefault("number_of_npd"           ).append(fmt(value=mvd.models[0].xray_structure_stat.all.n_npd  ))
      result.setdefault("occupancy_max"           ).append(fmt(value=mvd.models[0].xray_structure_stat.all.o_max ) )
      result.setdefault("occupancy_mean"          ).append(fmt(value=mvd.models[0].xray_structure_stat.all.o_mean) )
      result.setdefault("occupancy_min"           ).append(fmt(value=mvd.models[0].xray_structure_stat.all.o_min ) )

      result.setdefault("adp_max_all" ).append(fmt(value=mvd.models[0].xray_structure_stat.all.b_max ))
      result.setdefault("adp_mean_all").append(fmt(value=mvd.models[0].xray_structure_stat.all.b_mean))
      result.setdefault("adp_min_all" ).append(fmt(value=mvd.models[0].xray_structure_stat.all.b_min ))

      if(mvd.models[0].xray_structure_stat.sidechain is not None):
        result.setdefault("adp_max_sidechain" ).append(fmt(value=mvd.models[0].xray_structure_stat.sidechain.b_max ))
        result.setdefault("adp_mean_sidechain").append(fmt(value=mvd.models[0].xray_structure_stat.sidechain.b_mean))
        result.setdefault("adp_min_sidechain" ).append(fmt(value=mvd.models[0].xray_structure_stat.sidechain.b_min ))
      else:
        result.setdefault("adp_max_sidechain" ).append(fmt(value=None))
        result.setdefault("adp_mean_sidechain").append(fmt(value=None))
        result.setdefault("adp_min_sidechain" ).append(fmt(value=None))

      if(mvd.models[0].xray_structure_stat.backbone is not None):
        result.setdefault("adp_max_backbone" ).append(fmt(value=mvd.models[0].xray_structure_stat.backbone.b_max ))
        result.setdefault("adp_mean_backbone").append(fmt(value=mvd.models[0].xray_structure_stat.backbone.b_mean))
        result.setdefault("adp_min_backbone" ).append(fmt(value=mvd.models[0].xray_structure_stat.backbone.b_min ))
      else:
        result.setdefault("adp_max_backbone" ).append(fmt(value=None))
        result.setdefault("adp_mean_backbone").append(fmt(value=None))
        result.setdefault("adp_min_backbone" ).append(fmt(value=None))

      if(mvd.models[0].xray_structure_stat.solvent is not None):
        result.setdefault("adp_max_solvent" ).append(fmt(value=mvd.models[0].xray_structure_stat.solvent.b_max ))
        result.setdefault("adp_mean_solvent").append(fmt(value=mvd.models[0].xray_structure_stat.solvent.b_mean))
        result.setdefault("adp_min_solvent" ).append(fmt(value=mvd.models[0].xray_structure_stat.solvent.b_min ))
      else:
        result.setdefault("adp_max_solvent" ).append(fmt(value=None))
        result.setdefault("adp_mean_solvent").append(fmt(value=None))
        result.setdefault("adp_min_solvent" ).append(fmt(value=None))

  easy_pickle.dump("all_mvd.pickle", result)

if (__name__ == "__main__"):
  run()
