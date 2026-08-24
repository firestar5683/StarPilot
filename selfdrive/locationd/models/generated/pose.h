#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6369833963809703045);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4035234717988175099);
void pose_H_mod_fun(double *state, double *out_1402865724321173492);
void pose_f_fun(double *state, double dt, double *out_6035351479955239512);
void pose_F_fun(double *state, double dt, double *out_4841453483990746406);
void pose_h_4(double *state, double *unused, double *out_3927517291904970746);
void pose_H_4(double *state, double *unused, double *out_648704722266460885);
void pose_h_10(double *state, double *unused, double *out_6439648934382479816);
void pose_H_10(double *state, double *unused, double *out_4788307442778779812);
void pose_h_13(double *state, double *unused, double *out_7496824369401694209);
void pose_H_13(double *state, double *unused, double *out_4482460185568984909);
void pose_h_14(double *state, double *unused, double *out_6785183211401772861);
void pose_H_14(double *state, double *unused, double *out_3731493154561833181);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}