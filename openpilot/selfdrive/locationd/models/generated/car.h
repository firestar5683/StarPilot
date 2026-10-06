#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_9094620970440409675);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4808598882803507141);
void car_H_mod_fun(double *state, double *out_3453018442672977703);
void car_f_fun(double *state, double dt, double *out_2361277581367117895);
void car_F_fun(double *state, double dt, double *out_5103437232056083059);
void car_h_25(double *state, double *unused, double *out_948931866886974125);
void car_H_25(double *state, double *unused, double *out_69962207316513974);
void car_h_24(double *state, double *unused, double *out_6581862240582867615);
void car_H_24(double *state, double *unused, double *out_3627887806118837110);
void car_h_30(double *state, double *unused, double *out_4586381395140996475);
void car_H_30(double *state, double *unused, double *out_59376739826726096);
void car_h_26(double *state, double *unused, double *out_5529891248042658910);
void car_H_26(double *state, double *unused, double *out_3671541111557542250);
void car_h_27(double *state, double *unused, double *out_1706782012047792935);
void car_H_27(double *state, double *unused, double *out_2234140051627151007);
void car_h_29(double *state, double *unused, double *out_8858689410907709496);
void car_H_29(double *state, double *unused, double *out_450854604487666088);
void car_h_28(double *state, double *unused, double *out_2310097896724270452);
void car_H_28(double *state, double *unused, double *out_4631544412581864486);
void car_h_31(double *state, double *unused, double *out_803412042666319154);
void car_H_31(double *state, double *unused, double *out_100608169193474402);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}