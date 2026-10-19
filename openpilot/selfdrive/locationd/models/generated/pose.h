#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8706376808260214389);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1316013831039188305);
void pose_H_mod_fun(double *state, double *out_1995820263732979846);
void pose_f_fun(double *state, double dt, double *out_1989172059616365876);
void pose_F_fun(double *state, double dt, double *out_1876162241026325508);
void pose_h_4(double *state, double *unused, double *out_8913681603248625200);
void pose_H_4(double *state, double *unused, double *out_7148338648772060581);
void pose_h_10(double *state, double *unused, double *out_5957325102648707682);
void pose_H_10(double *state, double *unused, double *out_8659941392114727724);
void pose_h_13(double *state, double *unused, double *out_3800811769775255925);
void pose_H_13(double *state, double *unused, double *out_8086131599605158234);
void pose_h_14(double *state, double *unused, double *out_4008947375398857851);
void pose_H_14(double *state, double *unused, double *out_7335164568598006506);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}