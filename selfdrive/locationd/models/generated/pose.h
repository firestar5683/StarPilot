#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8427200704796300077);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_209888032840788679);
void pose_H_mod_fun(double *state, double *out_5010822586708507522);
void pose_f_fun(double *state, double dt, double *out_8028362113385460735);
void pose_F_fun(double *state, double dt, double *out_435032814721793170);
void pose_h_4(double *state, double *unused, double *out_5120020554280573886);
void pose_H_4(double *state, double *unused, double *out_6208770068591405626);
void pose_h_10(double *state, double *unused, double *out_1855806828650009923);
void pose_H_10(double *state, double *unused, double *out_86752177367218496);
void pose_h_13(double *state, double *unused, double *out_3472048471963902900);
void pose_H_13(double *state, double *unused, double *out_9025700179785813189);
void pose_h_14(double *state, double *unused, double *out_1446434657591522405);
void pose_H_14(double *state, double *unused, double *out_8274733148778661461);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}