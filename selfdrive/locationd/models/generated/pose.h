#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6404612215142923466);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8928511729536831732);
void pose_H_mod_fun(double *state, double *out_6801514816147998315);
void pose_f_fun(double *state, double dt, double *out_9011020625270980343);
void pose_F_fun(double *state, double dt, double *out_5745440695796585215);
void pose_h_4(double *state, double *unused, double *out_3972431218962943054);
void pose_H_4(double *state, double *unused, double *out_7873422047717645729);
void pose_h_10(double *state, double *unused, double *out_4525655768187115008);
void pose_H_10(double *state, double *unused, double *out_456117981794075216);
void pose_h_13(double *state, double *unused, double *out_37028039399378348);
void pose_H_13(double *state, double *unused, double *out_262790839400944800);
void pose_h_14(double *state, double *unused, double *out_8155163407200643054);
void pose_H_14(double *state, double *unused, double *out_7490533593696533591);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}