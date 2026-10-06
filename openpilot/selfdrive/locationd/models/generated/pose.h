#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8769047576014597915);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6606884682512325288);
void pose_H_mod_fun(double *state, double *out_3800934607722013466);
void pose_f_fun(double *state, double dt, double *out_6652247469516692531);
void pose_F_fun(double *state, double dt, double *out_8011247107029651568);
void pose_h_4(double *state, double *unused, double *out_1414268185846324142);
void pose_H_4(double *state, double *unused, double *out_5620633333628310327);
void pose_h_10(double *state, double *unused, double *out_485138144046796067);
void pose_H_10(double *state, double *unused, double *out_5435004367830975165);
void pose_h_13(double *state, double *unused, double *out_5970031784927357775);
void pose_H_13(double *state, double *unused, double *out_2408359508295977526);
void pose_h_14(double *state, double *unused, double *out_2427394029087566377);
void pose_H_14(double *state, double *unused, double *out_1657392477288825798);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}