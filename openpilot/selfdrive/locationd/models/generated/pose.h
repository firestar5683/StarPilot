#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4948547112888214127);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1637666684293454320);
void pose_H_mod_fun(double *state, double *out_2192054780204158214);
void pose_f_fun(double *state, double dt, double *out_8699512147542263638);
void pose_F_fun(double *state, double dt, double *out_5585604130229028810);
void pose_h_4(double *state, double *unused, double *out_7040990451462861704);
void pose_H_4(double *state, double *unused, double *out_8084524700677117702);
void pose_h_10(double *state, double *unused, double *out_5385759793768973690);
void pose_H_10(double *state, double *unused, double *out_522586112484741399);
void pose_h_13(double *state, double *unused, double *out_1659773189667427592);
void pose_H_13(double *state, double *unused, double *out_4872250875344784901);
void pose_h_14(double *state, double *unused, double *out_6941415956428537191);
void pose_H_14(double *state, double *unused, double *out_8519641227322001301);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}