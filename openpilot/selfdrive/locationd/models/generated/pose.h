#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_1314885097679334068);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2457185809051772100);
void pose_H_mod_fun(double *state, double *out_2842365525503581863);
void pose_f_fun(double *state, double dt, double *out_4467642216364550642);
void pose_F_fun(double *state, double dt, double *out_6705233003971863459);
void pose_h_4(double *state, double *unused, double *out_2420505654720678801);
void pose_H_4(double *state, double *unused, double *out_7994883910542662598);
void pose_h_10(double *state, double *unused, double *out_2313242717828257647);
void pose_H_10(double *state, double *unused, double *out_5472455547052034825);
void pose_h_13(double *state, double *unused, double *out_5520356542441325623);
void pose_H_13(double *state, double *unused, double *out_7239586337834556217);
void pose_h_14(double *state, double *unused, double *out_8136982398563814036);
void pose_H_14(double *state, double *unused, double *out_6488619306827404489);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}