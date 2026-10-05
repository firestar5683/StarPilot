#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_8386835163844872263);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5826204590882848019);
void pose_H_mod_fun(double *state, double *out_7521593534267777079);
void pose_f_fun(double *state, double dt, double *out_8190127916652503129);
void pose_F_fun(double *state, double dt, double *out_8302830792992532360);
void pose_h_4(double *state, double *unused, double *out_6664200415740758039);
void pose_H_4(double *state, double *unused, double *out_5772632154402693802);
void pose_h_10(double *state, double *unused, double *out_2232580687525306632);
void pose_H_10(double *state, double *unused, double *out_1994505413045679835);
void pose_h_13(double *state, double *unused, double *out_1739439411373720736);
void pose_H_13(double *state, double *unused, double *out_2560358329070361001);
void pose_h_14(double *state, double *unused, double *out_2162487226046509469);
void pose_H_14(double *state, double *unused, double *out_1809391298063209273);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}