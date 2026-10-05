#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_3094993718265680010);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_446507105452282601);
void pose_H_mod_fun(double *state, double *out_96002479082188485);
void pose_f_fun(double *state, double dt, double *out_8888553933023554192);
void pose_F_fun(double *state, double dt, double *out_3793856272932959588);
void pose_h_4(double *state, double *unused, double *out_10924150640940683);
void pose_H_4(double *state, double *unused, double *out_5752079327669770236);
void pose_h_10(double *state, double *unused, double *out_3400315615895606338);
void pose_H_10(double *state, double *unused, double *out_6603039364318987837);
void pose_h_13(double *state, double *unused, double *out_5162106749790850325);
void pose_H_13(double *state, double *unused, double *out_2539805502337437435);
void pose_h_14(double *state, double *unused, double *out_8034891048701220434);
void pose_H_14(double *state, double *unused, double *out_1788838471330285707);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}