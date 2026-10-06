#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_581108018479819489);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7407620403679899755);
void pose_H_mod_fun(double *state, double *out_6259423772009568262);
void pose_f_fun(double *state, double dt, double *out_855366903388822681);
void pose_F_fun(double *state, double dt, double *out_1978214635701427629);
void pose_h_4(double *state, double *unused, double *out_4297907286096878653);
void pose_H_4(double *state, double *unused, double *out_8079122497915865123);
void pose_h_10(double *state, double *unused, double *out_2075957019235364681);
void pose_H_10(double *state, double *unused, double *out_4849572450209365182);
void pose_h_13(double *state, double *unused, double *out_3557575460249098873);
void pose_H_13(double *state, double *unused, double *out_4866848672583532322);
void pose_h_14(double *state, double *unused, double *out_175200106668597994);
void pose_H_14(double *state, double *unused, double *out_7284833143498314197);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}