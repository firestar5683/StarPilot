#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_1002597543094682529);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6790221310632921126);
void pose_H_mod_fun(double *state, double *out_1061940044083541431);
void pose_f_fun(double *state, double dt, double *out_3240563005197080216);
void pose_F_fun(double *state, double dt, double *out_5982976038096974601);
void pose_h_4(double *state, double *unused, double *out_3015297743882558799);
void pose_H_4(double *state, double *unused, double *out_8440442363568188843);
void pose_h_10(double *state, double *unused, double *out_4712013892887729118);
void pose_H_10(double *state, double *unused, double *out_747450665488565157);
void pose_h_13(double *state, double *unused, double *out_413147883148967273);
void pose_H_13(double *state, double *unused, double *out_6794027884809029972);
void pose_h_14(double *state, double *unused, double *out_2902963862180291092);
void pose_H_14(double *state, double *unused, double *out_5357653931272816547);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}