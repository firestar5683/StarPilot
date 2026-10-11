#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5239387107130576177);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8017465374679690286);
void pose_H_mod_fun(double *state, double *out_3050146727026118690);
void pose_f_fun(double *state, double dt, double *out_7401195424910099109);
void pose_F_fun(double *state, double dt, double *out_7953355824038160444);
void pose_h_4(double *state, double *unused, double *out_5685529689104176696);
void pose_H_4(double *state, double *unused, double *out_8898228533778077411);
void pose_h_10(double *state, double *unused, double *out_5395236827797613020);
void pose_H_10(double *state, double *unused, double *out_4460820551654126260);
void pose_h_13(double *state, double *unused, double *out_5553209120626692209);
void pose_H_13(double *state, double *unused, double *out_5685954708445744610);
void pose_h_14(double *state, double *unused, double *out_8764675248435452423);
void pose_H_14(double *state, double *unused, double *out_4934987677438592882);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}