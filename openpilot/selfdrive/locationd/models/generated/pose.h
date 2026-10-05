#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4299274199831556809);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2345037795202932384);
void pose_H_mod_fun(double *state, double *out_2098398821367927813);
void pose_f_fun(double *state, double dt, double *out_5430492952832692036);
void pose_F_fun(double *state, double dt, double *out_8675558556930303753);
void pose_h_4(double *state, double *unused, double *out_4851457077302002369);
void pose_H_4(double *state, double *unused, double *out_900451339485029709);
void pose_h_10(double *state, double *unused, double *out_9193243756849124789);
void pose_H_10(double *state, double *unused, double *out_2799871591501321246);
void pose_h_13(double *state, double *unused, double *out_6658774396801807001);
void pose_H_13(double *state, double *unused, double *out_4734206802787553733);
void pose_h_14(double *state, double *unused, double *out_3195839728228906936);
void pose_H_14(double *state, double *unused, double *out_3983239771780402005);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}