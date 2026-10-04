#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7825504593440143444);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6707226023055995729);
void pose_H_mod_fun(double *state, double *out_4618881527044107692);
void pose_f_fun(double *state, double dt, double *out_6488051035785602820);
void pose_F_fun(double *state, double dt, double *out_733896468910208221);
void pose_h_4(double *state, double *unused, double *out_8117165171672920878);
void pose_H_4(double *state, double *unused, double *out_2162528408027234243);
void pose_h_10(double *state, double *unused, double *out_2185975476059121463);
void pose_H_10(double *state, double *unused, double *out_3758056759224999810);
void pose_h_13(double *state, double *unused, double *out_5359065950265790886);
void pose_H_13(double *state, double *unused, double *out_1049745417305098558);
void pose_h_14(double *state, double *unused, double *out_2243166911667620430);
void pose_H_14(double *state, double *unused, double *out_1800712448312250286);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}