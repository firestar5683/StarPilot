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
void car_err_fun(double *nom_x, double *delta_x, double *out_4155166221753319167);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6258424399114082833);
void car_H_mod_fun(double *state, double *out_9207883978122540712);
void car_f_fun(double *state, double dt, double *out_6099552525591428416);
void car_F_fun(double *state, double dt, double *out_6907019441075095165);
void car_h_25(double *state, double *unused, double *out_7654255320318543180);
void car_H_25(double *state, double *unused, double *out_45671869674773667);
void car_h_24(double *state, double *unused, double *out_3125065132614720384);
void car_H_24(double *state, double *unused, double *out_2126977729330725899);
void car_h_30(double *state, double *unused, double *out_2295828072127268444);
void car_H_30(double *state, double *unused, double *out_2564004828182022294);
void car_h_26(double *state, double *unused, double *out_5606219983362431125);
void car_H_26(double *state, double *unused, double *out_3695831449199282557);
void car_h_27(double *state, double *unused, double *out_3256303239036914168);
void car_H_27(double *state, double *unused, double *out_4787598899365965511);
void car_h_29(double *state, double *unused, double *out_7297501339788114089);
void car_H_29(double *state, double *unused, double *out_3074236172496414478);
void car_h_28(double *state, double *unused, double *out_6293089290481246853);
void car_H_28(double *state, double *unused, double *out_2008162844573116096);
void car_h_31(double *state, double *unused, double *out_1487141280347408877);
void car_H_31(double *state, double *unused, double *out_76317831551734095);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}