#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_5818094549552656547);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3606049234714008263);
void pose_H_mod_fun(double *state, double *out_1632125326007639956);
void pose_f_fun(double *state, double dt, double *out_6251314416692735066);
void pose_F_fun(double *state, double dt, double *out_4702066556653843398);
void pose_h_4(double *state, double *unused, double *out_6137997042648778710);
void pose_H_4(double *state, double *unused, double *out_5403932535851547528);
void pose_h_10(double *state, double *unused, double *out_5824027401609001493);
void pose_H_10(double *state, double *unused, double *out_5647838180481634355);
void pose_h_13(double *state, double *unused, double *out_5389816574077237163);
void pose_H_13(double *state, double *unused, double *out_8616206361183880329);
void pose_h_14(double *state, double *unused, double *out_364380652379967511);
void pose_H_14(double *state, double *unused, double *out_9079570681518519559);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}