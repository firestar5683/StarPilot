#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_1686705028277529867);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1103979266905204510);
void pose_H_mod_fun(double *state, double *out_3778009894403191156);
void pose_f_fun(double *state, double dt, double *out_8134339984135029222);
void pose_F_fun(double *state, double dt, double *out_4223035310147805923);
void pose_h_4(double *state, double *unused, double *out_3703400346234585599);
void pose_H_4(double *state, double *unused, double *out_7549817104247098728);
void pose_h_10(double *state, double *unused, double *out_1721115505953865677);
void pose_H_10(double *state, double *unused, double *out_8217499614069688590);
void pose_h_13(double *state, double *unused, double *out_4057181902355091495);
void pose_H_13(double *state, double *unused, double *out_7684653144130120087);
void pose_h_14(double *state, double *unused, double *out_3026553806307433649);
void pose_H_14(double *state, double *unused, double *out_4467028671951726432);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}