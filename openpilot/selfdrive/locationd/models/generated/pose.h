#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_1624039058015520117);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3394922841093355008);
void pose_H_mod_fun(double *state, double *out_5983346335611634108);
void pose_f_fun(double *state, double dt, double *out_2787475759251093193);
void pose_F_fun(double *state, double dt, double *out_3131463405263695248);
void pose_h_4(double *state, double *unused, double *out_4236476822836846053);
void pose_H_4(double *state, double *unused, double *out_135264528859675387);
void pose_h_10(double *state, double *unused, double *out_8903764653121362197);
void pose_H_10(double *state, double *unused, double *out_6671785341230841941);
void pose_h_13(double *state, double *unused, double *out_6817806490457608280);
void pose_H_13(double *state, double *unused, double *out_3347538354192008188);
void pose_h_14(double *state, double *unused, double *out_2340902130253582351);
void pose_H_14(double *state, double *unused, double *out_4098505385199159916);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}