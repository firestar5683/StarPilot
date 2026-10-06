#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8810353316368700687);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8282119777185922813);
void pose_H_mod_fun(double *state, double *out_9067879162073671719);
void pose_f_fun(double *state, double dt, double *out_6384990450931193177);
void pose_F_fun(double *state, double dt, double *out_105498423206002474);
void pose_h_4(double *state, double *unused, double *out_3142206333536839736);
void pose_H_4(double *state, double *unused, double *out_123517496015850377);
void pose_h_10(double *state, double *unused, double *out_7019642631864442983);
void pose_H_10(double *state, double *unused, double *out_8619357166475704864);
void pose_h_13(double *state, double *unused, double *out_7946660746268207299);
void pose_H_13(double *state, double *unused, double *out_3710237967286673647);
void pose_h_14(double *state, double *unused, double *out_6202390496101391785);
void pose_H_14(double *state, double *unused, double *out_2959270936279521919);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}