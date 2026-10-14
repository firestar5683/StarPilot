#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7101503095265833649);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4514359099843804277);
void pose_H_mod_fun(double *state, double *out_7558013151580796863);
void pose_f_fun(double *state, double dt, double *out_6874989583183873730);
void pose_F_fun(double *state, double dt, double *out_2414486911096174000);
void pose_h_4(double *state, double *unused, double *out_2032881575968680861);
void pose_H_4(double *state, double *unused, double *out_8312174153635509470);
void pose_h_10(double *state, double *unused, double *out_6246501970919422236);
void pose_H_10(double *state, double *unused, double *out_9105171975845846865);
void pose_h_13(double *state, double *unused, double *out_5690258237608804476);
void pose_H_13(double *state, double *unused, double *out_2523938711757341217);
void pose_h_14(double *state, double *unused, double *out_4651254816825442403);
void pose_H_14(double *state, double *unused, double *out_6171329063734557617);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}