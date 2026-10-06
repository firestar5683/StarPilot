#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5635938807142857948);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4989912554372507650);
void pose_H_mod_fun(double *state, double *out_1119877989261778800);
void pose_f_fun(double *state, double dt, double *out_2123753475159758437);
void pose_F_fun(double *state, double dt, double *out_2042072363153328823);
void pose_h_4(double *state, double *unused, double *out_2017169174657903512);
void pose_H_4(double *state, double *unused, double *out_2651929220582128772);
void pose_h_10(double *state, double *unused, double *out_7790822241274132646);
void pose_H_10(double *state, double *unused, double *out_1807588708691679220);
void pose_h_13(double *state, double *unused, double *out_5087328461209279336);
void pose_H_13(double *state, double *unused, double *out_5864203045914461573);
void pose_h_14(double *state, double *unused, double *out_8996928075667050682);
void pose_H_14(double *state, double *unused, double *out_6615170076921613301);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}