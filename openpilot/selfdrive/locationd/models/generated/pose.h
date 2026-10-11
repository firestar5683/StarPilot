#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4223042806110963609);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8530086622469742933);
void pose_H_mod_fun(double *state, double *out_8909363854772424894);
void pose_f_fun(double *state, double dt, double *out_1291447636833644141);
void pose_F_fun(double *state, double dt, double *out_2156602018501124106);
void pose_h_4(double *state, double *unused, double *out_6395852196578726056);
void pose_H_4(double *state, double *unused, double *out_5765573009093219150);
void pose_h_10(double *state, double *unused, double *out_7562508967147311156);
void pose_H_10(double *state, double *unused, double *out_4704156203817477126);
void pose_h_13(double *state, double *unused, double *out_4947379913658815439);
void pose_H_13(double *state, double *unused, double *out_2553299183760886349);
void pose_h_14(double *state, double *unused, double *out_4640800764138358777);
void pose_H_14(double *state, double *unused, double *out_1802332152753734621);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}