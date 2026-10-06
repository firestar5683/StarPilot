#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4574623741916747896);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2341160614075288752);
void pose_H_mod_fun(double *state, double *out_8733031835894533596);
void pose_f_fun(double *state, double dt, double *out_8868616660930423881);
void pose_F_fun(double *state, double dt, double *out_6060136886631410443);
void pose_h_4(double *state, double *unused, double *out_6022306051754618176);
void pose_H_4(double *state, double *unused, double *out_5164396188455542);
void pose_h_10(double *state, double *unused, double *out_7686741891596612442);
void pose_H_10(double *state, double *unused, double *out_6739799969353632287);
void pose_h_13(double *state, double *unused, double *out_2333214722145795372);
void pose_H_13(double *state, double *unused, double *out_3217438221520788343);
void pose_h_14(double *state, double *unused, double *out_2463064256028585948);
void pose_H_14(double *state, double *unused, double *out_429952130456428057);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}