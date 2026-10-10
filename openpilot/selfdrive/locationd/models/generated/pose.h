#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5983304822532396966);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6802128044019654079);
void pose_H_mod_fun(double *state, double *out_3170132304237044244);
void pose_f_fun(double *state, double dt, double *out_8255079778207779351);
void pose_F_fun(double *state, double dt, double *out_4238693480342293986);
void pose_h_4(double *state, double *unused, double *out_2471379555464088728);
void pose_H_4(double *state, double *unused, double *out_8322650689276124979);
void pose_h_10(double *state, double *unused, double *out_5249786927742937080);
void pose_H_10(double *state, double *unused, double *out_8433765414018862422);
void pose_h_13(double *state, double *unused, double *out_3320787694222680609);
void pose_H_13(double *state, double *unused, double *out_6911819559101093836);
void pose_h_14(double *state, double *unused, double *out_7880969684345092326);
void pose_H_14(double *state, double *unused, double *out_6160852528093942108);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}