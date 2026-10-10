#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8743288361506485614);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7700232313042684193);
void pose_H_mod_fun(double *state, double *out_5879762199447615362);
void pose_f_fun(double *state, double dt, double *out_9125558702662429027);
void pose_F_fun(double *state, double dt, double *out_7572446057115886568);
void pose_h_4(double *state, double *unused, double *out_2003156353488409837);
void pose_H_4(double *state, double *unused, double *out_9153984278238564615);
void pose_h_10(double *state, double *unused, double *out_8299050468126391648);
void pose_H_10(double *state, double *unused, double *out_2268983315058168095);
void pose_h_13(double *state, double *unused, double *out_8163970253337406046);
void pose_H_13(double *state, double *unused, double *out_1543353069921863686);
void pose_h_14(double *state, double *unused, double *out_7902513815616600364);
void pose_H_14(double *state, double *unused, double *out_5190743421899080086);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}