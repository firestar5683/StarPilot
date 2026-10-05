#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5541167196451846312);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_497075597603097975);
void pose_H_mod_fun(double *state, double *out_724419807350783906);
void pose_f_fun(double *state, double dt, double *out_6691116852918071868);
void pose_F_fun(double *state, double dt, double *out_3096830296170468775);
void pose_h_4(double *state, double *unused, double *out_9106257316383440258);
void pose_H_4(double *state, double *unused, double *out_8219941858707037436);
void pose_h_10(double *state, double *unused, double *out_423402028295143085);
void pose_H_10(double *state, double *unused, double *out_3774900494247078646);
void pose_h_13(double *state, double *unused, double *out_1499409244337466363);
void pose_H_13(double *state, double *unused, double *out_5007668033374704635);
void pose_h_14(double *state, double *unused, double *out_7703910231150666575);
void pose_H_14(double *state, double *unused, double *out_4256701002367552907);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}