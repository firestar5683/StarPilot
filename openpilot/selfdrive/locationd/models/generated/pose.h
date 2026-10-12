#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6908032543271437367);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6322019134835395929);
void pose_H_mod_fun(double *state, double *out_5045397248752443787);
void pose_f_fun(double *state, double dt, double *out_2578103679579667045);
void pose_F_fun(double *state, double dt, double *out_9023639176273047325);
void pose_h_4(double *state, double *unused, double *out_6773770520031459625);
void pose_H_4(double *state, double *unused, double *out_4456985158899286487);
void pose_h_10(double *state, double *unused, double *out_2891796970203767629);
void pose_H_10(double *state, double *unused, double *out_5240016567730035669);
void pose_h_13(double *state, double *unused, double *out_7766623268738295305);
void pose_H_13(double *state, double *unused, double *out_623229695596762463);
void pose_h_14(double *state, double *unused, double *out_3433693932581315158);
void pose_H_14(double *state, double *unused, double *out_1374196726603914191);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}