#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5143015347590812681);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1498290725825032559);
void pose_H_mod_fun(double *state, double *out_4606755190645614426);
void pose_f_fun(double *state, double dt, double *out_8576950781836710085);
void pose_F_fun(double *state, double dt, double *out_9071365926554278405);
void pose_h_4(double *state, double *unused, double *out_7694457163636602289);
void pose_H_4(double *state, double *unused, double *out_7880977269436563679);
void pose_h_10(double *state, double *unused, double *out_5236443719394936462);
void pose_H_10(double *state, double *unused, double *out_8689295297570059510);
void pose_h_13(double *state, double *unused, double *out_9075529594653175555);
void pose_H_13(double *state, double *unused, double *out_4668703444104230878);
void pose_h_14(double *state, double *unused, double *out_6684644170062039646);
void pose_H_14(double *state, double *unused, double *out_3917736413097079150);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}