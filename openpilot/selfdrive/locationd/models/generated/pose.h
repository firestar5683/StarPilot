#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_2840849685208399580);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2304315321105159078);
void pose_H_mod_fun(double *state, double *out_8772695675045116403);
void pose_f_fun(double *state, double dt, double *out_8679165298156092092);
void pose_F_fun(double *state, double dt, double *out_2287386913391151309);
void pose_h_4(double *state, double *unused, double *out_7225240582787038467);
void pose_H_4(double *state, double *unused, double *out_729686732606613871);
void pose_h_10(double *state, double *unused, double *out_6771917199724722492);
void pose_H_10(double *state, double *unused, double *out_1701889044214050319);
void pose_h_13(double *state, double *unused, double *out_348279363800690429);
void pose_H_13(double *state, double *unused, double *out_3941960557938946672);
void pose_h_14(double *state, double *unused, double *out_7323634935456606723);
void pose_H_14(double *state, double *unused, double *out_4692927588946098400);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}