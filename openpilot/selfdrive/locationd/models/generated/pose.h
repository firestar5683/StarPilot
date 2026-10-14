#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7355263616721595469);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8139235620588348311);
void pose_H_mod_fun(double *state, double *out_7307874178124431266);
void pose_f_fun(double *state, double dt, double *out_5281617793051128066);
void pose_F_fun(double *state, double dt, double *out_171852704988817231);
void pose_h_4(double *state, double *unused, double *out_2569970869827434637);
void pose_H_4(double *state, double *unused, double *out_8432009482317850141);
void pose_h_10(double *state, double *unused, double *out_3771666334899656059);
void pose_H_10(double *state, double *unused, double *out_783655174248384591);
void pose_h_13(double *state, double *unused, double *out_2343495232075740300);
void pose_H_13(double *state, double *unused, double *out_6802460766059368674);
void pose_h_14(double *state, double *unused, double *out_8726156210581630392);
void pose_H_14(double *state, double *unused, double *out_7996892955672966542);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}