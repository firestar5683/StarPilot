#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_2903893253895971355);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3928278332152438487);
void pose_H_mod_fun(double *state, double *out_5666984403538513454);
void pose_f_fun(double *state, double dt, double *out_3108653889513613454);
void pose_F_fun(double *state, double dt, double *out_3156103136607478463);
void pose_h_4(double *state, double *unused, double *out_4668712772901425910);
void pose_H_4(double *state, double *unused, double *out_3277377262519307888);
void pose_h_10(double *state, double *unused, double *out_5024807863031837328);
void pose_H_10(double *state, double *unused, double *out_4567419581298515838);
void pose_h_13(double *state, double *unused, double *out_711061843632216754);
void pose_H_13(double *state, double *unused, double *out_4333253945797393041);
void pose_h_14(double *state, double *unused, double *out_1546878073048898636);
void pose_H_14(double *state, double *unused, double *out_685863593820176641);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}