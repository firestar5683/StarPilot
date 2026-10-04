#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3009922513179117509);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_975857412122476284);
void pose_H_mod_fun(double *state, double *out_5701585413794445279);
void pose_f_fun(double *state, double dt, double *out_7100436431164388549);
void pose_F_fun(double *state, double dt, double *out_4695823766962492888);
void pose_h_4(double *state, double *unused, double *out_2886213327032254372);
void pose_H_4(double *state, double *unused, double *out_146496392957513442);
void pose_h_10(double *state, double *unused, double *out_1449862159655962354);
void pose_H_10(double *state, double *unused, double *out_3097566833981104856);
void pose_h_13(double *state, double *unused, double *out_2970086023674538452);
void pose_H_13(double *state, double *unused, double *out_3065777432374819359);
void pose_h_14(double *state, double *unused, double *out_2307174073331940796);
void pose_H_14(double *state, double *unused, double *out_3816744463381971087);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}