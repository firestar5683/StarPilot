#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4692908354627516438);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4642633870531563233);
void pose_H_mod_fun(double *state, double *out_999051991476226225);
void pose_f_fun(double *state, double dt, double *out_8595496590093260126);
void pose_F_fun(double *state, double dt, double *out_600705311639882547);
void pose_h_4(double *state, double *unused, double *out_2786040394933084983);
void pose_H_4(double *state, double *unused, double *out_1531113305230126453);
void pose_h_10(double *state, double *unused, double *out_2868077015136456598);
void pose_H_10(double *state, double *unused, double *out_3113914393471003549);
void pose_h_13(double *state, double *unused, double *out_3137887318351603650);
void pose_H_13(double *state, double *unused, double *out_2095715224911970557);
void pose_h_14(double *state, double *unused, double *out_6370524001895544374);
void pose_H_14(double *state, double *unused, double *out_1551675127065245843);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}