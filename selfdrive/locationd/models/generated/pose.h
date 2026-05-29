#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_867342344380239798);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2946458972277190645);
void pose_H_mod_fun(double *state, double *out_8034808007713849348);
void pose_f_fun(double *state, double dt, double *out_5448742405462655453);
void pose_F_fun(double *state, double dt, double *out_582733379073092242);
void pose_h_4(double *state, double *unused, double *out_959952002277923346);
void pose_H_4(double *state, double *unused, double *out_1467574399937880926);
void pose_h_10(double *state, double *unused, double *out_315403293584823803);
void pose_H_10(double *state, double *unused, double *out_2334763542090568144);
void pose_h_13(double *state, double *unused, double *out_5013407308002664142);
void pose_H_13(double *state, double *unused, double *out_4679848225270213727);
void pose_h_14(double *state, double *unused, double *out_6338305732819674146);
void pose_H_14(double *state, double *unused, double *out_1615214032357491370);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}