#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3597460724364137401);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1062002485999931142);
void pose_H_mod_fun(double *state, double *out_4662972867475177241);
void pose_f_fun(double *state, double dt, double *out_3840229658681249647);
void pose_F_fun(double *state, double dt, double *out_8220635292339759608);
void pose_h_4(double *state, double *unused, double *out_2097936204583725179);
void pose_H_4(double *state, double *unused, double *out_4839409540176553033);
void pose_h_10(double *state, double *unused, double *out_29444642201375045);
void pose_H_10(double *state, double *unused, double *out_1070049335288984001);
void pose_h_13(double *state, double *unused, double *out_61045813616994293);
void pose_H_13(double *state, double *unused, double *out_8051683365508885834);
void pose_h_14(double *state, double *unused, double *out_8545162578881105562);
void pose_H_14(double *state, double *unused, double *out_4404293013531669434);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}