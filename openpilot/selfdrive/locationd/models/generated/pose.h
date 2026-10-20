#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7083554587370275014);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6548503546481104197);
void pose_H_mod_fun(double *state, double *out_8484867830328864601);
void pose_f_fun(double *state, double dt, double *out_6058628880177520660);
void pose_F_fun(double *state, double dt, double *out_5197906072130444471);
void pose_h_4(double *state, double *unused, double *out_8442663857645814160);
void pose_H_4(double *state, double *unused, double *out_1223680011297697877);
void pose_h_10(double *state, double *unused, double *out_3964974043036968705);
void pose_H_10(double *state, double *unused, double *out_5914479273564375913);
void pose_h_13(double *state, double *unused, double *out_8876471781075959631);
void pose_H_13(double *state, double *unused, double *out_1988593814034634924);
void pose_h_14(double *state, double *unused, double *out_8405881405530134324);
void pose_H_14(double *state, double *unused, double *out_1658796537942581476);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}