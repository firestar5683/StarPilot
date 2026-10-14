#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5566842885647767369);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7605915063363770360);
void pose_H_mod_fun(double *state, double *out_9174940369185036217);
void pose_f_fun(double *state, double dt, double *out_4673717053718014348);
void pose_F_fun(double *state, double dt, double *out_7626949901910213403);
void pose_h_4(double *state, double *unused, double *out_2637904353676577);
void pose_H_4(double *state, double *unused, double *out_3423721897772556678);
void pose_h_10(double *state, double *unused, double *out_2208932603856339349);
void pose_H_10(double *state, double *unused, double *out_1086050679309335415);
void pose_h_13(double *state, double *unused, double *out_8307148822937221148);
void pose_H_13(double *state, double *unused, double *out_6635995723104889479);
void pose_h_14(double *state, double *unused, double *out_81297754970292080);
void pose_H_14(double *state, double *unused, double *out_7386962754112041207);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}