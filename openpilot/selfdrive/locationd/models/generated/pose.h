#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_1501121085238419754);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2556801483726826729);
void pose_H_mod_fun(double *state, double *out_839846666563197587);
void pose_f_fun(double *state, double dt, double *out_4964874563314269219);
void pose_F_fun(double *state, double dt, double *out_517376202194933410);
void pose_h_4(double *state, double *unused, double *out_1231289761953142672);
void pose_H_4(double *state, double *unused, double *out_1417903479331939554);
void pose_h_10(double *state, double *unused, double *out_5694367547801407568);
void pose_H_10(double *state, double *unused, double *out_412441903161159026);
void pose_h_13(double *state, double *unused, double *out_3834866587183286615);
void pose_H_13(double *state, double *unused, double *out_1794370346000393247);
void pose_h_14(double *state, double *unused, double *out_4481809147207636321);
void pose_H_14(double *state, double *unused, double *out_4500691911627311850);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}