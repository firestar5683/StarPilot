#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8753495689455606364);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7040060865599254852);
void pose_H_mod_fun(double *state, double *out_2703870827941122868);
void pose_f_fun(double *state, double dt, double *out_8883447168535687566);
void pose_F_fun(double *state, double dt, double *out_5352116671186116134);
void pose_h_4(double *state, double *unused, double *out_7227081021545178632);
void pose_H_4(double *state, double *unused, double *out_496539073160347156);
void pose_h_10(double *state, double *unused, double *out_1880125658668972037);
void pose_H_10(double *state, double *unused, double *out_6033877093640339494);
void pose_h_13(double *state, double *unused, double *out_7805785120847628893);
void pose_H_13(double *state, double *unused, double *out_68062846521496948);
void pose_h_14(double *state, double *unused, double *out_5362476079090588);
void pose_H_14(double *state, double *unused, double *out_3579327505455719452);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}