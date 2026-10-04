#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7611002709956289417);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2231207821854008376);
void pose_H_mod_fun(double *state, double *out_6702701208743020995);
void pose_f_fun(double *state, double dt, double *out_6952086026266534103);
void pose_F_fun(double *state, double dt, double *out_6422576820580893617);
void pose_h_4(double *state, double *unused, double *out_2343258124227340986);
void pose_H_4(double *state, double *unused, double *out_2731058445052846129);
void pose_h_10(double *state, double *unused, double *out_2458659875279043295);
void pose_H_10(double *state, double *unused, double *out_605941240178618613);
void pose_h_13(double *state, double *unused, double *out_819965896496064494);
void pose_H_13(double *state, double *unused, double *out_481215380279486672);
void pose_h_14(double *state, double *unused, double *out_4282191208550667364);
void pose_H_14(double *state, double *unused, double *out_1232182411286638400);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}