#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6507930050433723456);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4828699442560272840);
void pose_H_mod_fun(double *state, double *out_6044345162965507958);
void pose_f_fun(double *state, double dt, double *out_2707422486897363634);
void pose_F_fun(double *state, double dt, double *out_2783420399776033045);
void pose_h_4(double *state, double *unused, double *out_6625322830489649201);
void pose_H_4(double *state, double *unused, double *out_891826777926427223);
void pose_h_10(double *state, double *unused, double *out_495585793918053605);
void pose_H_10(double *state, double *unused, double *out_8682725662931185277);
void pose_h_13(double *state, double *unused, double *out_6437595282912769194);
void pose_H_13(double *state, double *unused, double *out_2320447047405905578);
void pose_h_14(double *state, double *unused, double *out_1731855561045144303);
void pose_H_14(double *state, double *unused, double *out_1326943304571310822);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}