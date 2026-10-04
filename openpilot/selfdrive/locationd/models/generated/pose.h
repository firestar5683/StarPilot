#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_932967681042200213);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3534086283432917024);
void pose_H_mod_fun(double *state, double *out_1261648596307961615);
void pose_f_fun(double *state, double dt, double *out_6850450012256179975);
void pose_F_fun(double *state, double dt, double *out_139005871191941126);
void pose_h_4(double *state, double *unused, double *out_6584047401950888130);
void pose_H_4(double *state, double *unused, double *out_3840307253386032882);
void pose_h_10(double *state, double *unused, double *out_6356449235196377560);
void pose_H_10(double *state, double *unused, double *out_2411644251267738056);
void pose_h_13(double *state, double *unused, double *out_8442951675068228609);
void pose_H_13(double *state, double *unused, double *out_6551790083508858);
void pose_h_14(double *state, double *unused, double *out_8458196630210230674);
void pose_H_14(double *state, double *unused, double *out_3640838561893707542);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}