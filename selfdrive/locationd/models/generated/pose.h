#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_486750963754107954);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1555487183493314770);
void pose_H_mod_fun(double *state, double *out_2668724034635220264);
void pose_f_fun(double *state, double dt, double *out_9201625055442330332);
void pose_F_fun(double *state, double dt, double *out_435223935958301203);
void pose_h_4(double *state, double *unused, double *out_6259395131604772748);
void pose_H_4(double *state, double *unused, double *out_4488422760541517125);
void pose_h_10(double *state, double *unused, double *out_8979834360034398189);
void pose_H_10(double *state, double *unused, double *out_5518597412603733548);
void pose_h_13(double *state, double *unused, double *out_627396395224579253);
void pose_H_13(double *state, double *unused, double *out_1276148935209184324);
void pose_h_14(double *state, double *unused, double *out_7453788352524990403);
void pose_H_14(double *state, double *unused, double *out_7571211192836889421);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}